FROM python:2.7.12

RUN apt-get update && apt-get install -y --no-install-recommends clang \
	&& rm -rf /var/lib/apt/lists/*

# Sane defaults for pip
ENV PIP_NO_CACHE_DIR off
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV PYTHONUNBUFFERED 1

RUN set -ex \
	&& version=3.4.3 \
	&& checksum=66b8d315c852908be9f79e1a18b8778714659fce4ddb2d041af8680a239202fc \
	&& wget "https://cmake.org/files/v3.4/cmake-$version-Linux-x86_64.tar.gz" \
	&& echo "$checksum  cmake-$version-Linux-x86_64.tar.gz" | sha256sum -c - \
	&& tar -xzf "cmake-$version-Linux-x86_64.tar.gz" --strip-components=1 -C /usr/local \
	&& rm "cmake-$version-Linux-x86_64.tar.gz"

ENV SYMSYND_LLVM_DIR /usr/src/symsynd/llvm
RUN mkdir -p $SYMSYND_LLVM_DIR \
	&& wget -O- https://github.com/llvm-mirror/llvm/archive/922af1cb46bb89a7bdbf68dfe77b15d1347441d7.tar.gz | tar -xz --strip-components=1 -C $SYMSYND_LLVM_DIR
RUN curl https://static.rust-lang.org/rustup.sh | sh -s -- --prefix=/usr/local --disable-sudo

RUN mkdir -p /usr/src/symsynd
WORKDIR /usr/src/symsynd
COPY . /usr/src/symsynd

ENTRYPOINT [ "make" ]
