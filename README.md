# Community Collections
A Research Computing Framework for Software Sharing

## Motivation, Citation

See our [paper](https://ssl.linklings.net/conferences/pearc/pearc19_program/views/includes/files/pap120s3-file1.pdf).

## Dependencies

* python
* wget
* bzip2

We are also assuming that the user's default shell is Bash.

## Quick Start

See our longer docs here: https://community-collections.github.io/ Otherwise, below is a 'Quick Start'.

### Testing as a user with admin privileges

Use the following commands to test the code.

```
# obtain community collections
git clone http://github.com/community-collections/community-collections
cd community-collections

# optional: clean ups if you intend to start over
./cc clean # only if you are developing and want to delete everything
# erase some stray module files because we do not clean them up
rm -rf ./modulefiles/julia ./modulefiles/lolcow ./modulefiles/R ./modulefiles/tensorflow
# clear your own cache if developing
rm -rf ~/.singularity ~/.cc_images 

# start here for the first time
./cc refresh
# we generate a cc.yaml so please have a look!
#   cc.yaml: remove error notes to build Lmod and Singularity locally if needed
vi cc.yaml 
# run cc refresh again after updating file
./cc refresh

# source initialization, user needs to affirm how cc is loaded into their environment
#   'cc profile' generates profile_cc.sh and adds it to ~/.bashrc (only contains references to Lmod)
./cc profile  
# if you wish to skip bashrc changes and only make the profile_cc.sh, use ./cc profile --no-bashrc
# source the file to enable cc
source profile_cc.sh # or get a new login shell if you said "y" to adding to your bashrc

# cc is live after you source a related file or agree to login shell mods
ml av # cc/conda supplies miniconda; cc/env supplies the conda env; and singularity is available as module

# if you are not root you may need to check if singularity is capable
./cc capable
sudo ./cc enable # sudo is required for sif files (no switch yet to enable sandboxes if you have userns)

# some examples of loading modules, community collections will 'pull' the image with the 
# combined power of Singularity and Lmod !
ml julia      # triggers the example singularity pull from docker
ml tensorflow # pulls a specific version with a suffix (see the default cc.yaml)
ml R          # gets a copy of R from r-base
```

Version checking and versionless modules are still under development.

### Testing in a container

The code is currently tested in a docker container with a very minimal set of requirements:

```
FROM centos:centos7
RUN yum update -y
RUN yum groupinstall -y 'Development Tools'
RUN yum install -y wget
RUN yum install -y which
RUN yum install -y vim
RUN yum install -y git
RUN yum install -y make
RUN yum install -y bzip2
RUN yum install -y cryptsetup
```

On a fresh VM with CentOS7:

```
# as root
yum update -y
yum groupinstall -y 'Development Tools'
yum install -y wget which vim git make bzip2 cryptsetup
```

Without `libtcl` or `squashfs-tools`, the code uses the `conda` environment to supply these. 

Note that very recent testing shows that cryptsetup is now required for later versions of Singularity 3.
