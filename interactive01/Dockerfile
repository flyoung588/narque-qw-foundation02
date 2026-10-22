FROM python@sha256:2ed6491b93cd49272ee6de2b5a38440c3448360322c089fc23e370722d74179d
ENV PYTHONPATH=/app OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
WORKDIR /app
RUN python -m pip install --no-cache-dir numpy==2.2.6 scipy==1.15.3 jsonschema==4.25.1 ase==3.29.0 pyscf==2.8.0
COPY foundation01 /app/foundation01
COPY router.py pyscf_adapter.py psi4_adapter.py /app/
COPY recovery02r /app/recovery02r
COPY qw_next /app/qw_next
COPY periodic02 /app/periodic02
COPY periodic03 /app/periodic03
COPY interactive01 /app/interactive01
ENTRYPOINT ["python","-B","/app/interactive01/cloud_run.py"]
