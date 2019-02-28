
export PATH=$HOME/miniconda/bin:$PATH

# wget is needed
# wget -N https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
# bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda -u

conda remove --name cc --all --yes
conda env create -n cc --file environment.yml

touch $HOME/.conda_cc_created

. $HOME/miniconda/etc/profile.d/conda.sh
conda activate cc

nvchecker ~/software/lmod/source.ini

new_ver=$(cut -d' ' -f2  ~/software/lmod/new_ver.txt)

SOFTWARE_TMP=$HOME/software/tmp
mkdir -p $SOFTWARE_TMP
cd $SOFTWARE_TMP

wget -N https://github.com/TACC/Lmod/archive/${new_ver}.tar.gz
tar xf ${new_ver}.tar.gz
cd Lmod-${new_ver}
./configure --prefix=$HOME/software && make install

