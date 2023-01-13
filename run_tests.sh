#!/bin/bash -x

if [ "$CI" == "true" ]; then
    pip3 install coverage

    set -e

    # To show migration logs
    ./manage.py test --keepdb -v 2 helix.tests

    # Now run all tests
    COVERAGE_PROCESS_START=`pwd`/.coveragerc coverage run -m py.test --reuse-db --durations=10

    # Collect/Generate reports
    coverage report -i
    coverage html -i
    coverage xml
    set +e
else
    py.test
fi
