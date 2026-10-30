# Prepared ONLY. No build or image pull performed in this tranche.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends gfortran && rm -rf /var/lib/apt/lists/*
COPY dynamics01/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY dynamics01/vendor/scalar_lsth.f90 /tmp/scalar_lsth.f90
COPY dynamics01/vendor/LICENSE /opt/qw-core/vendor/LICENSE
RUN gfortran -O2 -fPIC -shared /tmp/scalar_lsth.f90 -o /opt/qw-core/vendor/liblsth.so && rm /tmp/scalar_lsth.f90
ENV OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
WORKDIR /app
COPY . /app
