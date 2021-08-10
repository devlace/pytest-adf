# -*- coding: utf-8 -*-

import pytest
import os
import time
import logging
import json
from datetime import timedelta
from datetime import datetime
from pytest_adf.pytest_adf_enums import BlobEventType
from pytest_adf.pytest_adf_enums import TriggerRunDataAPIAction
from azure.identity import ClientSecretCredential, AzureCliCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from azure.mgmt.datafactory.models._models import RunQueryFilter
from azure.mgmt.datafactory.models._models import RunQueryOrderBy
from azure.mgmt.datafactory.models._models import RunFilterParameters
from azure.mgmt.datafactory.models._data_factory_management_client_enums import RunQueryOrderByField
from azure.mgmt.datafactory.models._data_factory_management_client_enums import RunQueryOrder
from azure.mgmt.datafactory.models._data_factory_management_client_enums import RunQueryFilterOperand
from azure.mgmt.datafactory.models._data_factory_management_client_enums import RunQueryFilterOperator
from azure.storage.blob import BlobServiceClient

LOG = logging.getLogger(__name__)

OPTIONAL_ARGS = ["AZ_SERVICE_PRINCIPAL_ID", "AZ_SERVICE_PRINCIPAL_SECRET", "AZ_STORAGE_ACCOUNT_NAME", "AZ_STORAGE_ACCOUNT_KEY"]
OPTIONAL_STORAGE_ACCOUNT_ARGS = ["AZ_STORAGE_ACCOUNT_NAME", "AZ_STORAGE_ACCOUNT_KEY"]
FETCHING_TRIGGER_RUNS_MAX_TIME_IN_SECONDS = 180
FETCHING_TRIGGER_RUNS_TIME_RANGE_IN_MINUTES = 3


def pytest_addoption(parser):
    group = parser.getgroup('adf')
    group.addoption(
        '--sp_id',
        action='store',
        dest='AZ_SERVICE_PRINCIPAL_ID',
        help='Service Principal Id use to connect to Azure'
    )
    group.addoption(
        '--sp_password',
        action='store',
        dest='AZ_SERVICE_PRINCIPAL_SECRET',
        help='Service Principal password/secret use to connect to Azure'
    )
    group.addoption(
        '--sp_tenant_id',
        action='store',
        dest='AZ_SERVICE_PRINCIPAL_TENANT_ID',
        help='Tenant Id of Service Principal use to connect to Azure'
    )
    group.addoption(
        '--sub_id',
        action='store',
        dest='AZ_SUBSCRIPTION_ID',
        help='Azure subscription id of Azure Data Factory'
    )
    group.addoption(
        '--rg_name',
        action='store',
        dest='AZ_RESOURCE_GROUP_NAME',
        help='Azure resource group of Azure Data Factory'
    )
    group.addoption(
        '--adf_name',
        action='store',
        dest='AZ_DATAFACTORY_NAME',
        help='Azure Data Factory name'
    )
    group.addoption(
        '--poll_interval',
        action='store',
        dest='AZ_DATAFACTORY_POLL_INTERVAL_SEC',
        help='Poll interval to query Data Factory status in seconds'
    )
    group.addoption(
        '--storage_account_name',
        action='store',
        dest='AZ_STORAGE_ACCOUNT_NAME',
        help='Azure Storage Account name; optional, only required if testing storage event triggered ADF pipelines'
    )
    group.addoption(
        '--storage_account_key',
        action='store',
        dest='AZ_STORAGE_ACCOUNT_KEY',
        help='Azure Storage Account key; optional, only required if testing storage event triggered ADF pipelines'
    )


@pytest.fixture(scope="session")
def adf_config(request):
    # Order of importance
    # 1. cmdline args
    # 2. environment variables
    def _default(val, default):
        return default if val is None else val
    r = request.config.option
    DEFAULT_AZ_DATAFACTORY_POLL_INTERVAL_SEC = 5
    config = {
        "AZ_SERVICE_PRINCIPAL_ID": _default(r.AZ_SERVICE_PRINCIPAL_ID, os.getenv("AZ_SERVICE_PRINCIPAL_ID")),
        "AZ_SERVICE_PRINCIPAL_SECRET": _default(r.AZ_SERVICE_PRINCIPAL_SECRET,
                                                os.getenv("AZ_SERVICE_PRINCIPAL_SECRET")),
        "AZ_SERVICE_PRINCIPAL_TENANT_ID": _default(r.AZ_SERVICE_PRINCIPAL_TENANT_ID,
                                                   os.getenv("AZ_SERVICE_PRINCIPAL_TENANT_ID")),
        "AZ_SUBSCRIPTION_ID": _default(r.AZ_SUBSCRIPTION_ID, os.getenv("AZ_SUBSCRIPTION_ID")),
        "AZ_RESOURCE_GROUP_NAME": _default(r.AZ_RESOURCE_GROUP_NAME, os.getenv("AZ_RESOURCE_GROUP_NAME")),
        "AZ_DATAFACTORY_NAME": _default(r.AZ_DATAFACTORY_NAME, os.getenv("AZ_DATAFACTORY_NAME")),
        "AZ_DATAFACTORY_POLL_INTERVAL_SEC": int(_default(r.AZ_DATAFACTORY_POLL_INTERVAL_SEC,
                                                         os.getenv("AZ_DATAFACTORY_POLL_INTERVAL_SEC",
                                                                   DEFAULT_AZ_DATAFACTORY_POLL_INTERVAL_SEC))),
        "AZ_STORAGE_ACCOUNT_NAME": _default(r.AZ_STORAGE_ACCOUNT_NAME, os.getenv("AZ_STORAGE_ACCOUNT_NAME")),
        "AZ_STORAGE_ACCOUNT_KEY": _default(r.AZ_STORAGE_ACCOUNT_KEY, os.getenv("AZ_STORAGE_ACCOUNT_KEY"))
    }
    # Ensure all required config is set.
    for config_key, value in config.items():
        if value is None and config_key not in OPTIONAL_ARGS:
            raise ValueError("Required config: {config_key} is not set.".format(config_key=config_key))

    return config


@pytest.fixture(scope="session")
def adf_client(adf_config):
    """Creates an DataFactoryManagementClient object"""
    if adf_config["AZ_SERVICE_PRINCIPAL_ID"] is None:
        credentials = AzureCliCredential()
    else:
        credentials = ClientSecretCredential(client_id=adf_config["AZ_SERVICE_PRINCIPAL_ID"],
                                         client_secret=adf_config["AZ_SERVICE_PRINCIPAL_SECRET"],
                                         tenant_id=adf_config["AZ_SERVICE_PRINCIPAL_TENANT_ID"])
    return DataFactoryManagementClient(credentials, adf_config["AZ_SUBSCRIPTION_ID"])


@pytest.fixture(scope="session")
def blob_service_client(adf_config):
    """Creates an BlobServiceClient object"""
    for arg in OPTIONAL_STORAGE_ACCOUNT_ARGS:
        if adf_config[arg] is None or adf_config[arg].isspace():
            raise ValueError("Required config for testing storage-event-triggered ADF pipelines: {} is not set properly.".format(arg))
    
    account_name = adf_config["AZ_STORAGE_ACCOUNT_NAME"]
    account_key = adf_config["AZ_STORAGE_ACCOUNT_KEY"]

    service_client = BlobServiceClient(
        account_url="https://" + account_name + ".blob.core.windows.net",
        credential=account_key
    )
    return service_client


@pytest.fixture(scope="session")
def adf_pipeline_run(adf_client, adf_config):
    """Factory function for triggering an ADF Pipeline run given run_inputs, and polls for results."""
    # Because ADF pipeline can be expensive to execute, you may want to cache pipeline_runs.
    # Cache pipeline runs are identified by pipeline_name and cached_run_name
    cached_pipeline_runs = {}

    def make_adf_pipeline_run(pipeline_name, run_inputs: dict, cached_run_name: str = "", rerun=False):
        # Check if pipeline run was already previous executed, simply return cached run
        if (cached_run_name != ""
            and not rerun
            and pipeline_name in cached_pipeline_runs.keys()
                and cached_run_name in cached_pipeline_runs[pipeline_name].keys()):
            LOG.info("""Previously executed cached pipeline run found for pipeline: {pipeline}
                     with run_name: {run_name}""".format(pipeline=pipeline_name, run_name=cached_run_name))
            return cached_pipeline_runs[pipeline_name][cached_run_name]

        # Trigger an ADF run
        az_resource_group = adf_config["AZ_RESOURCE_GROUP_NAME"]
        adf_name = adf_config["AZ_DATAFACTORY_NAME"]
        run_response = adf_client.pipelines.create_run(
            az_resource_group, adf_name, pipeline_name, parameters=run_inputs)
        pipeline_run = _poll_adf_until(adf_client, az_resource_group, adf_name, run_response.run_id,
                                       poll_interval=int(adf_config["AZ_DATAFACTORY_POLL_INTERVAL_SEC"]))

        # Store run in cache, if run_name is specified
        if cached_run_name != "":
            LOG.info("Caching pipeline: {pipeline} with run_name: {run_name}".format(
                pipeline=pipeline_name, run_name=cached_run_name))
            cached_pipeline_runs[pipeline_name] = {}
            cached_pipeline_runs[pipeline_name][cached_run_name] = pipeline_run
        return pipeline_run

    return make_adf_pipeline_run


def _poll_adf_until(adf_client, az_resource_group, adf_name, pipeline_run_id,
                    until_status=["Succeeded", "TimedOut", "Failed", "Cancelled"], poll_interval=5):
    """Helper function that polls ADF pipeline until specific status is achieved.
    Warning! may continue polling indefinitely if until_status is not set correctly.

    Args:
        adf_client (DataFactoryManagementClient): Azure Data Factory Management Client
        az_resource_group (str): Name of Azure Resource Group
        adf_name: Name of Azure Data Factory (ADF)
        pipeline_run_id (int): Run id of ADF pipeline to poll
        until_status (list[str], optional): List of ADF pipeline run status that will trigger end of polling.
            Defaults to ["Succeeded", "TimedOut", "Failed", "Cancelled"]
        poll_interval (int, optional): Poll interval in seconds. Defaults to 5.

    Returns:
        PipelineRun
    """
    pipeline_run_status = ""
    while (pipeline_run_status not in until_status):
        LOG.info("Polling pipeline with run id {} for status in {}".format(pipeline_run_id, ", ".join(until_status)))
        pipeline_run = adf_client.pipeline_runs.get(
            az_resource_group, adf_name, pipeline_run_id)
        pipeline_run_status = pipeline_run.status  # InProgress, Succeeded, Queued, TimedOut, Failed, Cancelled
        time.sleep(poll_interval)
    return pipeline_run


@pytest.fixture(scope="session")
def adf_storage_event_triggered_pipeline_run(adf_client, adf_config, blob_service_client):
    """Factory function for triggering an storage-event-triggered ADF Pipeline run by uploading target trigger file to storage account, and polls for results."""
    # Because ADF pipeline can be expensive to execute, you may want to cache pipeline_runs.
    # Cache pipeline runs are identified by pipeline_name and cached_run_name    
    cached_pipeline_runs = {}
    
    def make_adf_storage_event_triggered_pipeline_run(pipeline_name, 
                                                      trigger_name, 
                                                      trigger_file_path, 
                                                      container_name, 
                                                      local_trigger_file_path="", 
                                                      blob_event_type=BlobEventType.BLOB_CREATED, 
                                                      cached_run_name: str = "", 
                                                      rerun=False):
        
        # Check if pipeline run was already previous executed, simply return cached run
        if (cached_run_name != ""
            and not rerun
            and pipeline_name in cached_pipeline_runs.keys()
                and cached_run_name in cached_pipeline_runs[pipeline_name].keys()):
            LOG.info("""Previously executed cached pipeline run found for pipeline: {pipeline}
                     with run_name: {run_name}""".format(pipeline=pipeline_name, run_name=cached_run_name))
            return cached_pipeline_runs[pipeline_name][cached_run_name]
                
        az_resource_group = adf_config["AZ_RESOURCE_GROUP_NAME"]
        adf_name = adf_config["AZ_DATAFACTORY_NAME"]
        
        # Upload/delete event trigger file to/from target storage account, depends on given blob event type
        if blob_event_type == BlobEventType.BLOB_CREATED:
            blob_properties = _upload_event_trigger_file(blob_service_client, trigger_file_path, container_name, local_trigger_file_path)
        elif blob_event_type == BlobEventType.BLOB_DELETED:
            blob_properties = _delete_event_trigger_file(blob_service_client, trigger_file_path, container_name)
            
        # Fetch triggered pipeline run id from trigger run
        triggered_pipeline_run_id = _get_triggered_pipeline_run_id(adf_client, 
                                                                   az_resource_group, 
                                                                   adf_name, 
                                                                   pipeline_name, 
                                                                   trigger_name, 
                                                                   blob_event_type, 
                                                                   blob_properties["last_modified"], 
                                                                   blob_properties["etag"])
        
        pipeline_run = _poll_adf_until(adf_client, 
                                       az_resource_group, 
                                       adf_name, 
                                       triggered_pipeline_run_id, 
                                       poll_interval=int(adf_config["AZ_DATAFACTORY_POLL_INTERVAL_SEC"]))
        
        # Store run in cache, if run_name is specified
        if cached_run_name != "":
            LOG.info("Caching pipeline: {pipeline} with run_name: {run_name}".format(
                pipeline=pipeline_name, run_name=cached_run_name))
            cached_pipeline_runs[pipeline_name] = {}
            cached_pipeline_runs[pipeline_name][cached_run_name] = pipeline_run
        return pipeline_run
        
    return make_adf_storage_event_triggered_pipeline_run


def _upload_event_trigger_file(blob_service_client, trigger_file_path, container_name, local_trigger_file_path):
    """Helper function that upload event trigger file to target container of storage account.

    Args:
        blob_service_client (BlobServiceClient): Azure Storage Account service client
        trigger_file_path (str): Path of trigger file in storage account container
        container_name (str): Name of target container to upload the trigger file
        local_trigger_file_path (str): Local file path of the target trigger file.

    Returns:
        uploaded_blob_properties, including last modified time and eTag
    """
    blob_client = blob_service_client.get_blob_client(container_name, trigger_file_path)

    # Upload the event trigger file to starage account
    with open(local_trigger_file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    
    # Fetch eTag and last_modiefied from the uploaded event trigger file
    etag = blob_client.get_blob_properties().etag
    last_modified = blob_client.get_blob_properties().last_modified
    blob_properties = {
        "etag": etag.replace("\"", ""),
        "last_modified": last_modified
    }
    
    return blob_properties


def _delete_event_trigger_file(blob_service_client, trigger_file_path, container_name):
    """Helper function that delete event trigger file from target container of storage account.
    Warning: if target deleting file is not there, BlobNotFound exception will be raised.
    
    Args:
        blob_service_client (BlobServiceClient): Azure Storage Account service client
        trigger_file_path (str): Path of trigger file in storage account container
        container_name (str): Name of target container to upload the trigger file.

    Returns:
        blob_properties, including last modified time
    """
    container_client = blob_service_client.get_container_client(container_name)

    # Delete target event trigger file from storage account
    container_client.delete_blob(trigger_file_path)
    deleted_time = datetime.utcnow()
    blob_properties = {
        "etag": "",
        "last_modified": deleted_time
    }
    
    return blob_properties


def _get_triggered_pipeline_run_id(adf_client, az_resource_group, adf_name, pipeline_name, trigger_name, blob_event_type, trigger_file_last_modified_time, trigger_file_etag, poll_interval=5):
    """Helper functioin to get triggered pipeline run id by looking for expected trigger-run with last moified time and eTag of target event trigger file.
    Warning! TimeoutError exception may be raised if it still fails to find the expected trigger-run after the configured max time.
    """
    max_iterations = int(FETCHING_TRIGGER_RUNS_MAX_TIME_IN_SECONDS / poll_interval)
    iteration = 0
    found_trigger_run = False
    triggered_pipeline_run_id = ""
    while (found_trigger_run == False):
        LOG.info("Polling trigger-run by trigger name {}, last modified time and eTag of target trigger file.".format(trigger_name))
        
        if not found_trigger_run:
            run_query_filter = RunQueryFilter(operand=RunQueryFilterOperand.TRIGGER_NAME, operator=RunQueryFilterOperator.EQUALS, values=[trigger_name])
            run_query_order_by = RunQueryOrderBy(order_by=RunQueryOrderByField.TRIGGER_RUN_TIMESTAMP, order=RunQueryOrder.DESC)
            filter_params = RunFilterParameters(last_updated_after=trigger_file_last_modified_time, 
                                                last_updated_before=trigger_file_last_modified_time + timedelta(minutes = FETCHING_TRIGGER_RUNS_TIME_RANGE_IN_MINUTES),
                                                filters=[run_query_filter],
                                                order_by=[run_query_order_by])
            
            trigger_runs_query_response = adf_client.trigger_runs.query_by_factory(az_resource_group, 
                                                                                   adf_name, 
                                                                                   filter_params)
            trigger_runs = trigger_runs_query_response.value
            if (len(trigger_runs) > 0):
                for trigger_run in trigger_runs:
                    event_payload = trigger_run.properties.get("EventPayload")
                    event_payload_json = json.loads(event_payload.replace("\r\n", ""))
                    etag = event_payload_json["data"]["eTag"]
                    api = event_payload_json["data"]["api"]
                    
                    if ((blob_event_type == BlobEventType.BLOB_CREATED and api == TriggerRunDataAPIAction.PUT_BLOB and etag == trigger_file_etag) 
                        or (blob_event_type == BlobEventType.BLOB_DELETED and api == TriggerRunDataAPIAction.DELETE_BLOB)):
                        triggered_pipeline_run_id = trigger_run.triggered_pipelines.get(pipeline_name)
                        found_trigger_run = True
                        break
                        
        iteration += 1
        if iteration > max_iterations:
            raise TimeoutError("Time out when fetching expected trigger-run, please check relevant trigger configurations!")
        
        time.sleep(poll_interval)
    return triggered_pipeline_run_id
