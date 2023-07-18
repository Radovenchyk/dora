set -e

python3 -m venv .env
. $(pwd)/.env/bin/activate
# Dev dependencies
pip install maturin
pip install patchelf
cd ../../apis/python/node
maturin develop
cd ../../../examples/python-operator-dataflow

# Dependencies
pip install --upgrade pip
pip install -r requirements.txt

cargo run -p dora-daemon -- --run-dataflow dataflow_without_webcam.yml
