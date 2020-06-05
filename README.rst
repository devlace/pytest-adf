pytest-adf
==========

*ALPHA RELEASE*

pytest-adf is a `pytest <https://docs.pytest.org/en/stable/>`_ plugin for writing Azure Data Factory
integration tests. It is light-wrapper around the `Azure Data Factory
Python SDK <https://azure.github.io/azure-sdk-for-python/ref/Data-Factory.html?highlight=datafactory>`_.

Requirements
------------

You will need the following:

-  Python 3+

Installation
------------

To install pytest-adf:

.. code:: python

   pip install pytest-adf

Usage
-----

Here is a simple usage of the ``adf_pipeline_run`` fixture.

.. code:: python

   def test_pipeline_succeeded(adf_pipeline_run):
       this_run = adf_pipeline_run("my_pipeline", run_inputs={})
       assert this_run.status == "Succeeded"

The ``adf_pipeline_run`` fixture provides a factory function that
triggers a pipeline run when called. It will then block and poll the
pipeline run till completion\* before returning.

\*Pipeline run completion is defined by the following status:
"Succeeded", "TimedOut", "Failed", "Cancelled".

For more information see `Github page <https://aka.ms/pytest-adf>`_.