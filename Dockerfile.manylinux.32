FROM quay.io/pypa/manylinux1_i686
RUN linux32 yum -y install devtoolset-2-libstdc++-devel devtoolset-2-binutils-devel devtoolset-2-libatomic-devel gcc libffi-devel

ENV PIP_NO_CACHE_DIR off
ENV PIP_DISABLE_PIP_VERSION_CHECK on
ENV PYTHONUNBUFFERED 1

RUN set -ex \
	&& version=3.4.3 \
	&& checksum=5dfe85abe8cf176975efe0ac025eb00d0b796e887fd4471d0f39b0ee816d916c \
	&& wget --no-check-certificate "https://cmake.org/files/v3.4/cmake-$version-Linux-i386.tar.gz" \
	&& echo "$checksum  cmake-$version-Linux-i386.tar.gz" | sha256sum -c - \
	&& tar -xzf "cmake-$version-Linux-i386.tar.gz" --strip-components=1 -C /usr/local \
	&& rm "cmake-$version-Linux-i386.tar.gz"
RUN curl https://static.rust-lang.org/rustup.sh | linux32 sh -s -- --prefix=/usr/local --disable-sudo

ENV SYMSYND_MANYLINUX 1
ENV PATH "/opt/python/cp27-cp27mu/bin:$PATH"
RUN mkdir -p /usr/src/symsynd
WORKDIR /usr/src/symsynd
COPY . /usr/src/symsynd

ENTRYPOINT [ "linux32", "make", "MANYLINUX=1" ]
