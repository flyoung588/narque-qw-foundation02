FROM python@sha256:2ed6491b93cd49272ee6de2b5a38440c3448360322c089fc23e370722d74179d
ENV PYTHONPATH=/app OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 BLIS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 HOME=/tmp PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY state_space01/requirements-fixed.txt /tmp/requirements-fixed.txt
RUN python -m pip install --no-cache-dir --only-binary=:all: -r /tmp/requirements-fixed.txt
COPY foundation01 /app/foundation01
COPY router.py pyscf_adapter.py psi4_adapter.py /app/
COPY recovery02r /app/recovery02r
COPY qw_next /app/qw_next
COPY periodic02 /app/periodic02
COPY periodic03 /app/periodic03
COPY interactive01 /app/interactive01
COPY state_space01 /app/state_space01
COPY frontier01 /app/frontier01
ENTRYPOINT ["python","-B","/app/frontier01/cloud_run.py"]
