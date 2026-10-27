FROM python@sha256:2ed6491b93cd49272ee6de2b5a38440c3448360322c089fc23e370722d74179d
ENV PYTHONPATH=/app OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
WORKDIR /app
RUN python -m pip install --no-cache-dir numpy==2.2.6 scipy==1.15.3 jsonschema==4.25.1 ase==3.29.0 pyscf==2.8.0
COPY router.py /app/
COPY foundation01 /app/foundation01
COPY qw_next /app/qw_next
COPY recovery02r /app/recovery02r
COPY live01 /app/live01
COPY birth01 /app/birth01
COPY world01 /app/world01
COPY interactive01 /app/interactive01
COPY frontier01 /app/frontier01
COPY state_space01 /app/state_space01
COPY periodic03 /app/periodic03
