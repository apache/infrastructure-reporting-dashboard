FROM python:3.11

ENV \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN DEBIAN_FRONTEND='noninteractive' apt-get update -y

RUN DEBIAN_FRONTEND='noninteractive' apt-get --no-install-recommends install -y \
    wget apt-utils curl sqlite3 ldap-utils apache2 syslog-ng

RUN echo "ServerName infra-reports.local" > /etc/apache2/conf-enabled/servername.conf
RUN a2enmod proxy proxy_http

WORKDIR /tmp

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY docker-config/000-default.conf /etc/apache2/sites-enabled
COPY docker-config/asfldapsearch /usr/bin

WORKDIR /var/www

EXPOSE 8000
EXPOSE 80

ENTRYPOINT ["/var/www/docker-config/start.sh"]

