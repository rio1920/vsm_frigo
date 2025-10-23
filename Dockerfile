FROM python:3.13 as backend
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID myuser && useradd -m -u $UID -g $GID myuser

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# sap nwrfc sdk installation
RUN mkdir /usr/local/sap
RUN mkdir /usr/local/sap/nwrfcsdk
COPY ./sap/nwrfcsdk /usr/local/sap/nwrfcsdk
# set the SAPNWRFC_HOME env variable
ENV SAPNWRFC_HOME /usr/local/sap/nwrfcsdk
# Include the lib directory in the library search path
ENV LD_LIBRARY_PATH /usr/local/sap/nwrfcsdk/lib
# copy nwrfcsdk configuration file
COPY ./sap/nwrfcsdk.conf /etc/ld.so.conf.d/nwrfcsdk.conf
# run the command ldconfig
RUN ldconfig
# install cython
RUN pip install Cython
# install pyrfc from tar.gz
COPY ./sap/pyrfc-3.3.1.tar.gz /sap/pyrfc-3.3.1.tar.gz
RUN pip install /sap/pyrfc-3.3.1.tar.gz


RUN pip install uv

COPY uv.lock pyproject.toml /app/
RUN uv sync

CMD ["uv", "run", "manage.py", "runserver", "0.0.0.0:8000"]