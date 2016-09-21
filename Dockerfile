FROM ubuntu:devel

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        clang \
        curl \
        g++ \
        gcc-4.8 \
        g++-4.8 \
        python-pip \
        python-setuptools \
        python-dev \
        libffi-dev \
        libxml2-dev \
        libxml2-dev \
	zlib1g-dev \
	libncurses5-dev \

        # Extra dev tooling
        make \
        vim-nox \
        less \
        ntp \
	wget \
    && rm -rf /var/lib/apt/lists/*

# Sane defaults for pip
ENV PIP_NO_CACHE_DIR off
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV PYTHONUNBUFFERED 1

RUN wget --no-check-certificate http://cmake.org/files/v3.4/cmake-3.4.3-Linux-x86_64.tar.gz \
	&& tar -xzf cmake-3.4.3-Linux-x86_64.tar.gz
ENV PATH /cmake-3.4.3-Linux-x86_64/bin:$PATH

WORKDIR /symsynd
ADD . /symsynd
RUN mkdir -p /symsynd/llvm; mkdir -p /symsynd/build

ENTRYPOINT [ "make" ]
