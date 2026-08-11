FROM debian:bookworm-slim
# Official Brother DCP-T220 Linux LPR driver (downloaded at build time,
# not redistributed in this repo). Filter chain: PS -> ghostscript(ppmraw)
# -> brdcpt220filter -> application/vnd.brother-hbp
ARG DRV_URL=https://download.brother.com/welcome/dlf105164/dcpt220pdrv-3.5.0-1.i386.deb
RUN apt-get update && apt-get install -y --no-install-recommends \
        ghostscript perl file ca-certificates curl binutils \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL -o /tmp/drv.deb "$DRV_URL" \
    && cd /tmp && ar x drv.deb && tar xzf data.tar.gz -C / \
    && rm -f /tmp/drv.deb /tmp/*.tar.gz /tmp/debian-binary \
    && ln -s /opt/brother/Printers/dcpt220/lpd/x86_64/brdcpt220filter /opt/brother/Printers/dcpt220/lpd/brdcpt220filter \
    && ln -s /opt/brother/Printers/dcpt220/lpd/x86_64/brprintconf_dcpt220 /opt/brother/Printers/dcpt220/lpd/brprintconf_dcpt220 \
    && sed -i 's/PageSize=Letter/PageSize=A4/' /opt/brother/Printers/dcpt220/inf/brdcpt220rc \
    && chmod +x /opt/brother/Printers/dcpt220/lpd/filter_dcpt220 \
                /opt/brother/Printers/dcpt220/lpd/x86_64/brdcpt220filter
ENTRYPOINT ["/opt/brother/Printers/dcpt220/lpd/filter_dcpt220"]
