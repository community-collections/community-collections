# community-collections
A Research Computing Framework for Software Sharing


## Dependencies
* python
* wget
* bzip2

## Development notes

### Testing

Use the following commands to test the code.

```
git clone http://github.com/kmanalo/community-collections
cd community-collections
./cc nuke # only if you are developing and want to delete everything
rm -rf ~/.singularity ~/.cc_images # clear your own cache if developing
./cc refresh
vi cc.yaml # remove error notes to build Lmod and Singularity locally
./cc update_bashrc # generates profile_cc.sh and adds it to ~/.bashrc (only contains references to Lmod)
source profile_cc.sh # or get a new login shell if you said "y" to adding to your bashrc
ml av # cc/conda supplies miniconda; cc/env supplies the conda env; and singularity is available as module
./cc admin_check
sudo ./cc admin_check --force # sudo is required for sif files (no switch yet to enable sandboxes if you have userns)
ml julia # triggers the example singularity pull from docker
```

Version-checking and versionless modules are still under development.

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
RUN yum install -y screen
RUN yum install -y bzip2
```

Without `libtcl` or `squashfs-tools`, the code uses the `conda` environment to supply these. 