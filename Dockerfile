# Dev container with PySide6 built from source
FROM stateoftheartio/qt6:6.7-gcc-aqt
ARG QT_VERSION=6.7

# Install python 3.12
USER root
RUN apt-get update \
    && apt-get install -y software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    libgl1-mesa-dev \
    git \
    p7zip \
    libpython3-dev \
    python3.12-dev \
    python3.12-venv \
    python3.12-distutils
# clang \
# libclang-10-dev \
# ENV LLVM_INSTALL_DIR=/usr/lib/llvm-10

# Cleanup
RUN sudo apt-get clean && sudo rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set up virtualenv
USER user
WORKDIR /home/user
RUN mkdir -p ~/.virtualenvs \
    && python3.12 -m venv ~/.virtualenvs/pyside6 \
    && . ~/.virtualenvs/pyside6/bin/activate \
    && python -m pip install -U pip setuptools

# Install pre-built libclang
RUN curl -fLo libclang.7z https://download.qt.io/development_releases/prebuilt/libclang/libclang-release_140-based-linux-Ubuntu20.04-gcc9.3-x86_64.7z \
    && 7zr x libclang.7z \
    && rm libclang.7z
ENV LLVM_INSTALL_DIR=/home/user/libclang

# Check out pyside6 setup repo
RUN git clone https://code.qt.io/pyside/pyside-setup \
    && cd /home/user/pyside-setup \
    && QT_TAG=$(git tag | grep '^[v?]${QT_VERSION}' | tail -n 1) \
    && echo "Selecting PySide6 $QT_TAG" \
    && git checkout $QT_TAG

# Install dependencies and build with setuptools wrapper scripts
RUN cd /home/user/pyside-setup \
    && . ~/.virtualenvs/pyside6/bin/activate \
    && python -m pip install -r requirements.txt \
    && python setup.py build --parallel=4 --ignore-git \
    && python setup.py install --parallel=4

# Alternative: Build with cmake only, without setuptools
# BROKEN; Must be missing some cmake flags

# Misc hacks
# Why is this needed?? Otherwise fails with:
# stdcomplex.cpp:8:1: error: function 'StdComplex::StdComplex()' defaulted on its redeclaration with an exception-specification that differs from the implicit exception-specification ''
# sed -i /home/user/pyside-setup/sources/shiboken6/tests/libsample/stdcomplex.cpp -e 's/StdComplex::StdComplex() noexcept = default;//'
# hiddenobject.cpp:18:29: error: use of deleted function 'HiddenObject::HiddenObject()'
# In file included from /home/user/pyside-setup/sources/pyside6/tests/pysidetest/hiddenobject.cpp:4:
# hiddenobject.h:16:5: note: 'HiddenObject::HiddenObject() noexcept' is implicitly deleted because its exception-specification does not match the implicit exception-specification ''
# sed -i /home/user/pyside-setup/sources/pyside6/tests/pysidetest/hiddenobject.h -e 's/HiddenObject::HiddenObject() noexcept = default;//'

# Python headers not found
# export CPPFLAGS=-I/usr/include/python3.12
# export CMAKE_INCLUDE_PATH=/usr/include/python3.12

# Build with cmake (BROKEN)
# RUN cmake -B /home/user/pyside-setup/build \
#     -S /home/user/pyside-setup \
#     -DCMAKE_INSTALL_PREFIX=/home/user/pyside-setup/dist \
#     -DPython_EXECUTABLE=$HOME/.virtualenvs/pyside6/bin/python \
#     && cmake --build /home/user/pyside-setup/build --parallel 2 \
#     && cmake --install /home/user/pyside-setup/build
