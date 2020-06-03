# -*- coding: utf-8 -*-


def test_adf_config_fixture(testdir):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    testdir.makepyfile("""
        import pytest
        import os

        os.environ["AZ_DATAFACTORY_NAME"] = "adf_wrong" # Should be NOT be set, -- set in cmdline args
        os.environ["AZ_DATAFACTORY_POLL_INTERVAL_SEC"] = "10" # Should be set, -- not set in cmdline args

        def test_sth(adf_config):
            assert adf_config["AZ_SERVICE_PRINCIPAL_ID"] == "sp_id"
            assert adf_config["AZ_SERVICE_PRINCIPAL_SECRET"] == "sp_pass"
            assert adf_config["AZ_SERVICE_PRINCIPAL_TENANT_ID"] == "tenant_id"
            assert adf_config["AZ_SUBSCRIPTION_ID"] == "sub_id"
            assert adf_config["AZ_RESOURCE_GROUP_NAME"] == "rg"
            assert adf_config["AZ_DATAFACTORY_NAME"] == "adf"
            assert adf_config["AZ_DATAFACTORY_POLL_INTERVAL_SEC"] == 10
    """)

    # run pytest with the following cmd args
    result = testdir.runpytest(
        '--sp_id=sp_id',
        '--sp_password=sp_pass',
        '--sp_tenant_id=tenant_id',
        '--sub_id=s_id',
        '--sp_tenant_id=tenant_id',
        '--sub_id=sub_id',
        '--rg_name=rg',
        '--adf_name=adf',
        '-v'
    )

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0

# def test_adf_client_fixture(testdir):
#     # create a temporary pytest test module
#     testdir.makeconftest("""
#         import pytest
#         from azure.common.credentials import ServicePrincipalCredentials

#         @pytest.fixture(scope="session", autouse=True)
#         def do_something(session_mocker):
#             session_mocker.patch(ServicePrincipalCredentials, autospec=True)
#     """)
#     testdir.makepyfile("""
#         import pytest
#         from azure.mgmt.datafactory import DataFactoryManagementClient

#         def test_sth(adf_client):
#             assert isinstance(adf_client, DataFactoryManagementClient)
#     """)
#     # run pytest with the following cmd args
#     result = testdir.runpytest(
#         '--sp_id=sp_id',
#         '--sp_password=sp_pass',
#         '--sp_tenant_id=tenant_id',
#         '--sub_id=s_id',
#         '--sp_tenant_id=tenant_id',
#         '--sub_id=sub_id',
#         '--rg_name=rg',
#         '--adf_name=adf',
#         '-v'
#     )

#     # fnmatch_lines does an assertion internally
#     result.stdout.fnmatch_lines([
#         '*::test_sth PASSED*',
#     ])

#     # make sure that that we get a '0' exit code for the testsuite
#     assert result.ret == 0

