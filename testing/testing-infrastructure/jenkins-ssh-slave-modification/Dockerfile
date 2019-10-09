FROM jenkins/ssh-slave
MAINTAINER Sean Donovan <sdonovan@gatech.edu>

# https://github.com/ciena/mininet-docker/blob/master/Dockerfile
# Incorporating some lessons from this.

USER root
RUN apt update && apt -y install \
    python-pip \
    openvswitch-switch \
    mininet \
    curl \
    iproute2 \
    iputils-ping \
    net-tools \
    tcpdump \
    sudo \
    apt-utils \
    python3 \
    python3-pip 

RUN sleep 1
RUN apt install -y psmisc
RUN pip install virtualenv
RUN pip3 install virtualenv

RUN usermod -aG sudo jenkins
RUN echo "jenkins ALL=(root) NOPASSWD:ALL" > /etc/sudoers  && \
    chmod 0440 /etc/sudoers
    
EXPOSE 6633 6653 6640

COPY runtime-setup /usr/local/bin/runtime-setup

ENTRYPOINT ["runtime-setup"]

