FROM mambaorg/micromamba:2.3.2
USER root
RUN micromamba create -y -n science -c conda-forge python=3.11 psi4=1.9.1=py311h2ae924c_7 numpy=1.26.4 scipy=1.14.1 pip && micromamba clean --all --yes
RUN /opt/conda/envs/science/bin/python -m pip install --no-cache-dir pyscf==2.8.0 ase==3.29.0 jsonschema==4.25.1
ENV PATH=/opt/conda/envs/science/bin:$PATH PYTHONPATH=/app HOME=/tmp OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY . /app
ENTRYPOINT ["python","-B","/app/cloud/run.py"]
