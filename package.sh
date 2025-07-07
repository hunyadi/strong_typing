set -e

PYTHON_EXECUTABLE=${PYTHON:-python3}

# Clean up output from previous runs
if [ -d dist ]; then rm -rf dist; fi
if [ -d *.egg-info ]; then rm -rf *.egg-info; fi

# Run static type checker and unit tests
./check.sh

# Create PyPI package for distribution
$PYTHON_EXECUTABLE -m build --sdist --wheel

# Test PyPI package with various Python versions
for PYTHON_VERSION in 3.9 3.10 3.11 3.12 3.13
do
    docker build -t py-$PYTHON_VERSION-image --build-arg PYTHON_VERSION=$PYTHON_VERSION .
    docker run -i -t --rm py-$PYTHON_VERSION-image python3 -m unittest discover tests
    docker rmi py-$PYTHON_VERSION-image
done
