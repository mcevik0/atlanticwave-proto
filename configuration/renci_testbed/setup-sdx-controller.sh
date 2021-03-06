#!/bin/bash

AW_REPO="https://github.com/atlanticwave-sdx/atlanticwave-proto.git"
AW_BRANCH="master"

while getopts "R:B:" opt; do
    case $opt in
        R)
            AW_REPO=${OPTARG}
            ;;
        B)
            AW_BRANCH=${OPTARG}
            ;;
    esac
done

# yum work
if [[ $EUID -eq 0 ]]; then
  sudo yum -y update
  sudo yum -y install git docker-ce
fi

#sudo groupadd docker #Already added
#sudo usermod -aG docker $USER

# git work
echo "--- $0 : AW_REPO  : ${AW_REPO}"
echo "--- $0 : AW_BRANCH: ${AW_BRANCH}"
git clone ${AW_REPO}

# Docker work: build SDX Controller container
cd atlanticwave-proto
git checkout ${AW_BRANCH}
cp configuration/renci_testbed/renci_ben.manifest docker/sdx_container/

if [[ $EUID -eq 0 ]]; then
  #sudo systemctl restart docker
  sudo systemctl restart docker
fi

cd docker/sdx_container
sed -r -i "s/master/${AW_BRANCH}/g" Dockerfile
docker build -t sdx_container .
rm -f renci_ben.manifest 

# Copy over run scripts
cd ../../configuration/renci_testbed
cp start-sdx-controller.sh ~
