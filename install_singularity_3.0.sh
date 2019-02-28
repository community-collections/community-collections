#sudo yum -y update && \
#    sudo yum -y groupinstall 'Development Tools' && \
#    sudo yum -y install libarchive-devel
    sudo yum -y install openssl-devel
    sudo yum -y install libuuid-devel

#export VERSION=1.11 OS=linux ARCH=amd64
#cd /tmp
#wget https://dl.google.com/go/go$VERSION.$OS-$ARCH.tar.gz
#sudo tar -C /usr/local -xzf go$VERSION.$OS-$ARCH.tar.gz

#echo 'export GOPATH=${HOME}/go' >> ~/.bashrc
#echo 'export PATH=/usr/local/go/bin:${PATH}:${GOPATH}/bin' >> ~/.bashrc
source ~/.bashrc

mkdir -p $GOPATH/src/github.com/sylabs
cd $GOPATH/src/github.com/sylabs
# git clone https://github.com/sylabs/singularity.git
cd singularity
