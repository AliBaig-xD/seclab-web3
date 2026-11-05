# Custom Mythril: upgrade py-solc-x (old one points at a dead solc host) and
# pre-cache solc versions at build time so analysis works reliably offline.
FROM mythril/myth:latest
USER root
RUN pip install --no-cache-dir -U py-solc-x \
 && python -c "import solcx; [solcx.install_solc(v) for v in ['0.6.12','0.7.6','0.8.19','0.8.20','0.8.23','0.8.28']]"
