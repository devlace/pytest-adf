# -*- coding: utf-8 -*-

import os


def test_adf_config_fixture(testdir):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    testdir.makepyfile("""
        import pytest

        @pytest.fixture(autouse=True)
        def env_setup(monkeypatch):
            monkeypatch.setenv("AZ_DATAFACTORY_NAME", "adf_wrong")  # Should be set, as this is not set in cmdline args
            monkeypatch.setenv("AZ_DATAFACTORY_POLL_INTERVAL_SEC", "10")  # Should be set, as this is not set in cmdline args

        def test_sth(env_setup, adf_config):
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


# def test_help_message(testdir):
#     result = testdir.runpytest(
#         '--help',
#     )
#     # fnmatch_lines does an assertion internally
#     result.stdout.fnmatch_lines([
#         'adf:',
#         '*--foo=DEST_FOO*Set the value for the fixture "bar".',
#     ])


# def test_hello_ini_setting(testdir):
#     testdir.makeini("""
#         [pytest]
#         HELLO = world
#     """)

#     testdir.makepyfile("""
#         import pytest

#         @pytest.fixture
#         def hello(request):
#             return request.config.getini('HELLO')

#         def test_hello_world(hello):
#             assert hello == 'world'
#     """)

#     result = testdir.runpytest('-v')

#     # fnmatch_lines does an assertion internally
#     result.stdout.fnmatch_lines([
#         '*::test_hello_world PASSED*',
#     ])

#     # make sure that that we get a '0' exit code for the testsuite
#     assert result.ret == 0
