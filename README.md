
# pytest-adf

*ALPHA RELEASE*

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
The `adf_pipeline_run` fixture provides a factory function that triggers a pipeline run when called. It will then block and poll the pipeline run till completion* before returning.

*Pipeline run completion is defined by the following status: "Succeeded", "TimedOut", "Failed", "Cancelled".

For additional usage information, see [caching pipeline runs](#Caching-pipeline-runs).

## Configuration

You need to provide pytest-adf with the necessary configuration to connect to your Azure Data Factory. You can provide it via Environment Variables or as pytest command line variables. Command line variables take precendence over Environment Variables.

### Environment variables:
- **AZ_SERVICE_PRINCIPAL_ID** - Azure AD Service Principal with rights to trigger a run in Data Factory (ei. Data Factory Contributor)
- **AZ_SERVICE_PRINCIPAL_SECRET** - Password of Service Principal
- **AZ_SERVICE_PRINCIPAL_TENANT_ID** - Azure AD Tenant ID of Service Principal
- **AZ_SUBSCRIPTION_ID** - Azure Subscription ID where Azure Data Factory is hosted.
- **AZ_RESOURCE_GROUP_NAME** - Azure Resource Group name where Azure Data Factory is hosted.
- **AZ_DATAFACTORY_NAME** - Name of the Azure Data Factory.
- **AZ_DATAFACTORY_POLL_INTERVAL_SEC** - Optional. Seconds between poll intervals to check for status of the triggered run.

For more information on how to create an Azure AD service principal, see [here](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal).

### Commandline
Alternatively, you can pass these like so:
```
pytest
    --sp_id=my_sp_id \
    --sp_password=my_sp_pass \
    --sp_tenant_id=my_tenant_id \
    --sub_id=my_s_id \
    --rg_name=my_rg \
    --adf_name=my_adf \
    --poll_interval=20
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