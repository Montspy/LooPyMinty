FROM python:3 AS build
# upgrade pip
RUN pip install --upgrade pip
# add build pkgs
#RUN apk add --update gcc libc-dev jpeg-dev zlib-dev \
#&& rm  -rf /tmp/* /var/cache/apk/*
# install python modules
ADD requirements.txt /
ADD hello_loopring/requirements.txt /loopring.txt
RUN pip install -r /requirements.txt -r /loopring.txt

FROM python:3 AS run
# get compiled modules from pervious stage
COPY --from=build /usr/local/lib/python3.10 /usr/local/lib/python3.10
# add the python files for the game
ADD run.sh /usr/local/bin/run
# finish up container
WORKDIR /loopmintpy
CMD ["run"]
