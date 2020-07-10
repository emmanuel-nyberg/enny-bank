FROM python:3.8

ADD . /app
WORKDIR /app
EXPOSE 80
RUN export DEBIAN_FRONTEND=noninteractive && pip3 install pipenv &&\
    pipenv install && apt update && apt install -yq nginx && cp /app/nginx.conf /etc/nginx/nginx.conf &&\
    rm -rf /var/cache/apt
