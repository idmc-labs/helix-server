#!/bin/bash -x

if [ "$CI" == "true" ]; then
    pip3 install coverage

    set -e

    COVERAGE_PROCESS_START=`pwd`/.coveragerc coverage run -m py.test --durations=10

    # Collect/Generate reports
    coverage report -i
    coverage html -i
    coverage xml
    set +e
else
    py.test
fi
