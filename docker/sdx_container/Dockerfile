FROM ubuntu:16.04

RUN apt update && apt install -y git python-virtualenv pypy python-pip net-tools

# Virtualenv setup
RUN virtualenv -p /usr/bin/pypy /appenv
RUN . /appenv/bin/activate
#run pip install dataset

# Setup the PYTHONPATH script
ENV PYTHONPATH $PYTHONPATH:/atlanticwave-proto

COPY run_sdx.sh .
COPY ./*.manifest ./

# This really should point to a particular version
RUN git clone -b master https://github.com/atlanticwave-sdx/atlanticwave-proto.git
RUN cat atlanticwave-proto/requirements.txt
RUN pip install -r atlanticwave-proto/requirements.txt

CMD /bin/bash run_sdx.sh; /bin/bash
#CMD /bin/bash
