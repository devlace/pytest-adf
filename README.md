
# pytest-adf

This is an *ALPHA RELEASE*

pytest-adf is a [pytest](https://docs.pytest.org/en/stable/) plugin for writing Azure Data Factory integration tests. It is light-wrapper around the [Azure Data Factory Python SDK](https://azure.github.io/azure-sdk-for-python/ref/Data-Factory.html?highlight=datafactory).

[![Build Status](https://dev.azure.com/devlacepub/pytest-adf/_apis/build/status/ci-cd?branchName=master)](https://dev.azure.com/devlacepub/pytest-adf/_build/latest?definitionId=10&branchName=master)

## Requirements

You will need the following:

- Python 3+

## Installation

To install pytest-adf:

```python
pip install pytest-adf
```

## Usage

Here is a simple usage of the `adf_pipeline_run` fixture.

```python
def test_pipeline_succeeded(adf_pipeline_run):
    this_run = adf_pipeline_run("my_pipeline", run_inputs={})
    assert this_run.status == "Succeeded"
```

The `adf_pipeline_run` fixture provides a factory function that triggers a pipeline run when called. It will then block and poll the pipeline run till completion* before returning. Pipeline run completion is defined by the following status: "Succeeded", "TimedOut", "Failed", "Cancelled".

For an example of how to use this in an overall Modern Data Warehouse solution as part of an automated Azure DevOps Release Pipeline, see [here](https://github.com/Azure-Samples/modern-data-warehouse-dataops/blob/master/e2e_samples/parking_sensors/tests/integrationtests) and [here](https://github.com/Azure-Samples/modern-data-warehouse-dataops/blob/master/e2e_samples/parking_sensors/devops/templates/jobs/integration-tests-job.yml). This is part of a [larger demo solution](https://github.com/Azure-Samples/modern-data-warehouse-dataops/tree/master/e2e_samples/parking_sensors) showcasing DataOps as applied to the Modern Data Warehouse architecture.

For additional usage information, see [caching pipeline runs](#Caching-pipeline-runs).

### Testing Storage Event Triggered Pipelines
For testing storage event triggered pipelines, please use another fixture `adf_storage_event_triggered_pipeline_run`.

**Storage Event: BlobCreated**

For testing blob created event triggered pipelines, unlike `adf_pipeline_run` fixture, below extra arguments are required.
- trigger name, the configured trigger of the test target pipeline
- trigger file path, where to store the event trigger file in container
- storage account container name, together with trigger file path, the fixture knows where to upload the event trigger file
- local trigger file path, tells the fixture which even trigger file to upload
- blob event type, `BlobCreated` is the default value

The fixture firstly helps uploading declared storage event trigger file to target container of storage account to trigger the storage-event-triggered pipeline. Then it will block and poll related triggered pipeline run till completion* before returning. Pipeline run completion definition is same as above.

```python
PIPELINE_NAME = "my_blobcreated_event_triggered_pipeline"
TRIGGER_NAME = "storage_blob_created_event_trigger"
TRIGGER_FILE_PATH = "event-check/TR_BLOB_CREATED_STORAGE_EVENT.txt"
CONTAINER_NAME = "event-trigger"
LOCAL_TRIGGER_FILE_PATH = "./resources/TR_BLOB_CREATED_STORAGE_EVENT.txt"

def test_pipeline_succeeded(adf_storage_event_triggered_pipeline_run):
    this_run = adf_storage_event_triggered_pipeline_run(PIPELINE_NAME,
                                                        TRIGGER_NAME,
                                                        TRIGGER_FILE_PATH,
                                                        CONTAINER_NAME,
                                                        LOCAL_TRIGGER_FILE_PATH,
                                                        blob_event_type="BlobCreated") # Default value
    
    assert this_run.status == "Succeeded"
```

**Storage Event: BlobDeleted**

For testing blob deleted event triggered pipelines, please refer to below sample, which just skips the local-trigger-file-path argument and assigns `BlobDeleted` value to *blob_event_type* explicitly, then the fixture will help to delete declared event trigger file from the target container to trigger the specified pipeline run.

```python
PIPELINE_NAME = "my_blobdeleted_event_triggered_pipeline"
TRIGGER_NAME = "storage_blob_deleted_event_trigger"
TRIGGER_FILE_PATH = "event-check/TR_BLOB_DELETED_STORAGE_EVENT.txt"
CONTAINER_NAME = "event-trigger"

def test_pipeline_succeeded(adf_storage_event_triggered_pipeline_run):
    this_run = adf_storage_event_triggered_pipeline_run(PIPELINE_NAME,
                                                        TRIGGER_NAME,
                                                        TRIGGER_FILE_PATH,
                                                        CONTAINER_NAME,
                                                        blob_event_type="BlobDeleted")
    
    assert this_run.status == "Succeeded"
```

Note that 
- since pipeline parameters are required to set default values when adding/editing pipeline triggers, therefore there's no *run_inputs* argument for this fixture.
- since this fixture also helps to upload/delete event trigger file to/from storage account, we need additional storage account related environment variables, more details please refers to below *Environment Variables* section.
- please also provide the target event trigger file as test resources when testing `BlobCreated` event trigger pipelines.
- this fixture also supports caching pipeline runs, just append those two required arguments to enable it, for more details, please see [caching pipeline runs](#Caching-pipeline-runs).


## Configuration

You need to provide pytest-adf with the necessary configuration to connect to your Azure Data Factory. You can provide it via Environment Variables or as pytest command line variables. Command line variables take precedence over Environment Variables.

### Environment Variables

- **AZ_SERVICE_PRINCIPAL_ID** - Azure AD Service Principal with rights to trigger a run in Data Factory (ei. Data Factory Contributor), if not provided the test will use AZ-Cli authentication
- **AZ_SERVICE_PRINCIPAL_SECRET** - Password of Service Principal
- **AZ_SERVICE_PRINCIPAL_TENANT_ID** - Azure AD Tenant ID of Service Principal
- **AZ_SUBSCRIPTION_ID** - Azure Subscription ID where Azure Data Factory is hosted.
- **AZ_RESOURCE_GROUP_NAME** - Azure Resource Group name where Azure Data Factory is hosted.
- **AZ_DATAFACTORY_NAME** - Name of the Azure Data Factory.
- **AZ_DATAFACTORY_POLL_INTERVAL_SEC** - Optional. Seconds between poll intervals to check for status of the triggered run.
- **AZ_STORAGE_ACCOUNT_NAME** - Optional. Only required if testing storage event triggered Azure Data Factory pipelines.
- **AZ_STORAGE_ACCOUNT_KEY** - Optional. Only required if testing storage event triggered Azure Data Factory pipelines.

For more information on how to create an Azure AD service principal, see [here](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal).

### pytest command-line

Alternatively, you can pass these like so:

```
# Last two parameters are required only for testing storage event triggered pipelines
pytest
    --sp_id=my_sp_id \
    --sp_password=my_sp_pass \
    --sp_tenant_id=my_tenant_id \
    --sub_id=my_s_id \
    --rg_name=my_rg \
    --adf_name=my_adf \
    --poll_interval=20 \
    --storage_account_name=my_blob_storage_account \
    --storage_account_key=my_blob_storage_account_key
```

## Caching pipeline runs

Because ADF pipelines can be expensive to run, the `adf_pipeline_run` fixture allows you to cache pipeline runs by specifying the `cached_run_name` variable. Pipeline runs are identified by a combination of `pipeline_name` and `cached_run_name`. This is helpful is you want to create multiple test cases against the same pipeline_run without the needing to (1) rerun the entire pipeline or (2) mixing all assert statements in the same `test_` case function.

To force a rerun with the same pipeline_name and cached_run_name, use `rerun=True`.

For example:

```python
# Call adf_pipeline_run specifying cached_run_name variable.
this_first_run = adf_pipeline_run(pipeline_name="pipeline_foo", run_inputs={}, cached_run_name="run_bar")

# Call adf_pipeline_run again, with same pipeline_name and cached_run_name
# This will NOT trigger an actual ADF pipeline run, and will instead return this_first_run object.
# Note: run_inputs are not checked to determine if cached run was called with the same run_inputs.
this_second_run = adf_pipeline_run(pipeline_name="pipeline_foo", run_inputs={}, cached_run_name="run_bar")
this_first_run == this_second_run  # True

# To force a rerun, set rerun=True.
this_third_run = adf_pipeline_run(pipeline_name="pipeline_foo", run_inputs={}, cached_run_name="run_bar", rerun=True)
this_first_run != this_third_run  # False

```

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
