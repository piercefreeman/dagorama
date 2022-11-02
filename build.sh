#! /bin/bash -e

scriptPath=$(realpath $0)
rootDirectory="$(dirname "$scriptPath")"

# Remove old cached files
rm -rf $rootDirectory/build
rm -rf $rootDirectory/dagorama-broker/dagorama_broker/assets/dagorama

# Build
mkdir -p $rootDirectory/build
(cd $rootDirectory/broker && go build -o $rootDirectory/build)

# Manual Python install
cp $rootDirectory/build/dagorama $rootDirectory/dagorama-broker/dagorama_broker/assets/dagorama
