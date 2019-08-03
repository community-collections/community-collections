# Community Collections

Community Collections (CC) is an open-source high-performance computing (HPC)
framework which provides a seamless interface between
[Lmod](https://lmod.readthedocs.io/en/latest/) and [Singularity
containers](https://sylabs.io/singularity/) so that users can download and
deploy software in a Singularity container using the elegant module Lmod
system. The CC tool is useful for administrators who wish to install or detect
both Lmod and Singularity, customize a list of containers from public sources
([Docker Hub](https://hub.docker.com/)), [Singularity
Hub](https://singularity-hub.org/), and [Sylabs Cloud
Library](https://cloud.sylabs.io/library)).

Requirements
------------

1. Linux
2. A root-installed Singularity or else we will install one for you, and give you the opportunity to enable it with root
3. "Development Tools" including the [`gcc`](https://gcc.gnu.org/) compiler
4. `bzip2` for obvious reasons
5. `git` to get the code
6. `wget` to get necessary components
7. The `cryptsetup` package for installing recent versions of Singularity
8. A kernel with user namespaces if you lack root and wish to use Singularity sandbox containers instead of image files

The code is tested in two primary use cases. Users can install the code on a relatively minimal machine with the following Dockerfile.

<a name="dockerfile"></a>
~~~
FROM centos:centos7
RUN yum update -y
RUN yum groupinstall -y 'Development Tools'
RUN yum install -y wget
RUN yum install -y which
RUN yum install -y git
RUN yum install -y bzip2
RUN yum install -y cryptsetup
~~~

When you install community collections on the minimal system described above,
it will use Miniconda to providing supporting software such as `tcl` and
`squashfs-tools` and also compile `Singularity` and `Lmod` from their latest
available source distributions.

Alternately, it can be deployed on a standard HPC resource. The code is
designed to automatically detect preexisting Lmod and Singularity
installations. The most important feature of Community Collections is its
ability to *add container-driven modules to Lmod*.

Installation
------------

You can install a copy of Community Collections by cloning the source code and
running a single "refresh" command. This command will first install a
[Miniconda](https://docs.conda.io/en/latest/miniconda.html) environment to
provide supporting software (more on this later), and then either detect or
install Singularity and Lmod.

~~~
git clone http://github.com/community-collections/community-collections
cd community-collections
./cc refresh
~~~

What happens when you run "refresh"?
------------------------------------

Each time you run the `./cc refresh` command, it executes the following loop.

1. Install the python environment to `./miniconda` and point the `./cc` executable to use that environment. This provides a consistent python environment.
2. Read the `cc.yaml` file or write the default one.
3. Check for Singularity and Lmod and if they are not registered in `cc.yaml`. If they are not detected automatically, the code will ask you to edit the file. You can either provide the path to the existing installations, or more likely, ask the program to build them on the next "refresh".
4. If both Lmod and Singularity are ready, the refresh command will automatically generate the module tree from the "whitelist" in `cc.yaml`.
5. The user can customize the whitelist and then run `./cc refresh` again to update the module tree.

Case 1: A minimal system with root
----------------------------------

To deploy CC on the minimal system given by the [docker container above](#dockerfile), you only need to run the refresh function.

~~~
$ git clone http://github.com/community-collections/community-collections
$ cd community-collections
$ ./cc refresh
[CC] [STATUS] reading cache.json
[CC] [STATUS] failed to find cache so running bootstrap again
[CC] [STATUS] establishing environment
[CC] [STATUS] cannot find conda
[CC] [STATUS] installing miniconda
status executing the following script
| set -e
| set -x
| # environment here
| 
| set pipefail
| tmpdir=$(mktemp -d)
| here=$(pwd)
| cd $tmpdir
| echo "[STATUS] temporary build directory is $tmpdir"
| # build here
| 
| wget --progress=bar:force https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
| bash Miniconda3-latest-Linux-x86_64.sh -b -p /home/rpb/community-collections/miniconda -u
| 
| cd $here
| rm -rf $tmpdir
+ set pipefail
++ mktemp -d
+ tmpdir=/tmp/tmp.sQGCSCsUJJ
++ pwd
+ here=/home/rpb/community-collections
+ cd /tmp/tmp.sQGCSCsUJJ
+ echo '[STATUS] temporary build directory is /tmp/tmp.sQGCSCsUJJ'
[STATUS] temporary build directory is /tmp/tmp.sQGCSCsUJJ
~~~

The output continues as the program installs a Miniconda environment and a set of supporting software. When it is done, you will see the following "error" message.

~~~
[CC] [STATUS] done building the environment
[CC] [STATUS] writing cache.json
[CC] [STATUS] running a subshell to complete the installation
[CC] [STATUS] reading cache.json
[CC] [STATUS] writing default settings
[CC] [STATUS] inferring use case
[CC] [ERROR] caught error during "lmod"
[CC] [STATUS] received error: Failed to find Lmod. Need build path from the user.
[CC] [ERROR] caught error during "singularity"
[CC] [STATUS] received error: Failed to find Singularity. Need build path from the user.
[CC] [STATUS] Edit cc.yaml and rerun to continue.
[CC] [STATUS] writing cache.json
~~~

At this point, CC has failed to find Singularity or Lmod. Edit the default `cc.yaml` file to authorize a build. This is our ***settings*** file.

~~~
# cc.yaml
images: ~/.cc_images
lmod:
  build: ./lmod
  error: ERROR. Remove this note and follow these instructions to continue. Cannot
    locate Lmod. Set the `build` key to a desired installation location, remove this
    error, and refresh to continue.
module_settings:
  source: docker
singularity:
  build: ./singularity
  error: ERROR. Remove this note and follow these instructions to continue. Cannot
    locate Singularity. Set the `build` key to a desired installation location, remove
    this error, and refresh to continue.
  sandbox: false
whitelist:
  R:
    calls:
    - R
    - Rscript
    repo: r-base
    source: docker
    version: '>=3.6'
  julia:
    source: docker
    version: '>=1.0.1'
  lolcow:
    repo: leconte/examples/lolcow
    source: library
    version: latest
  tensorflow:
    calls:
    - python
    gpu: true
    repo: tensorflow/tensorflow
    shell: false
    source: docker
    version: 1.12.3-gpu-py3
~~~

If you remove the `error` entries in the `lmod` and `singularity` sections, the
settings file will instruct the program to build Lmod and Singularity at the
locations given by the `build` keys. Run `./cc refresh` to start building the
code.

If your system supplies `lua` with `lfs`, the Lua filesystem package, them Lmod
will use that, otherwise it compiles its own copy. Miniconda also supplies
`tcl` with headers since they are absent on our minimal system.

When the installation is complete, the code will report that it is ready.

~~~
[CC] [STATUS] reading cache.json
[CC] [STATUS] found settings at cc.yaml
[CC] [STATUS] inferring use case
[CC] [STATUS] Lmod is reporting ready
[CC] [STATUS] checking singularity
[CC] [STATUS] Singularity is reporting ready
[CC] [STATUS] community-collections is ready!
[CC] [STATUS] cache is unchanged
~~~

You can ignore the cache for now. The next step is to use root permissions to
enable singularity. First you can check the Singularity installation with the
`capable` command.

~~~
$ ./cc capable
[CC] [STATUS] reading cache.json
[CC] [WARNING] root must own: ./singularity/libexec/singularity/bin/starter-suid
[CC] [WARNING] root must own: ./singularity/etc/singularity/singularity.conf
[CC] [WARNING] root must own: ./singularity/etc/singularity/capability.json
[CC] [WARNING] root must own: ./singularity/etc/singularity/ecl.toml
[CC] [STATUS] run the following commands as root to give singularity the standard permissions: 

chown root:root ./singularity/etc/singularity/singularity.conf
chown root:root ./singularity/etc/singularity/capability.json
chown root:root ./singularity/etc/singularity/ecl.toml
chown root:root ./singularity/libexec/singularity/bin/starter-suid
chmod 4755 ./singularity/libexec/singularity/bin/starter-suid

[CC] [STATUS] Run "sudo ./cc enable" to do this automatically.
[CC] [STATUS] cache is unchanged
~~~

You can run these commands yourself, or use the following sudo command. Either
way, they will assign root ownership and the correct suid bit to the necessary
Singularity components.

~~~
sudo ./cc enable
[CC] [STATUS] reading cache.json
[CC] [WARNING] root must own: ./singularity/libexec/singularity/bin/starter-suid
[CC] [WARNING] root must own: ./singularity/etc/singularity/singularity.conf
[CC] [WARNING] root must own: ./singularity/etc/singularity/capability.json
[CC] [WARNING] root must own: ./singularity/etc/singularity/ecl.toml
[CC] [STATUS] run the following commands as root to give singularity the standard permissions: 

chown root:root ./singularity/etc/singularity/singularity.conf
chown root:root ./singularity/etc/singularity/capability.json
chown root:root ./singularity/etc/singularity/ecl.toml
chown root:root ./singularity/libexec/singularity/bin/starter-suid
chmod 4755 ./singularity/libexec/singularity/bin/starter-suid

[CC] [STATUS] Run "sudo ./cc enable" to do this automatically.
[CC] [STATUS] attempting to run the commands above
[CC] [STATUS] executing the following script
| chown root:root ./singularity/etc/singularity/singularity.conf
| chown root:root ./singularity/etc/singularity/capability.json
| chown root:root ./singularity/etc/singularity/ecl.toml
| chown root:root ./singularity/libexec/singularity/bin/starter-suid
| chmod 4755 ./singularity/libexec/singularity/bin/starter-suid
[CC] [STATUS] cache is unchanged
~~~

Beware that this will fail on disks with `nosuid`.

Using the code requires only that you generate a short profile script, which
you can optionally append to your existing `.bashrc`.

~~~
$ ./cc profile
[CC] [STATUS] reading cache.json
[CC] [STATUS] to use CC, run: source /home/rpb/community-collections/profile_cc.sh
[CC] [STATUS] proposed modifications to ~/.bashrc:
source /home/rpb/community-collections/profile_cc.sh
[QUESTION] okay to add the above to your ~/.bashrc? (y/N)?  
[CC] [STATUS] cache is unchanged
~~~

<a name="profile"></a>
The `profile_cc.sh` script adds a new moduletree to Lmod and sets the correct environment variables to use singularity.

~~~
# profile_cc.sh
post_add_luarc () { if [ -s "$1" ] && [[ ":$LMOD_RC:" != *":$1:"* ]]; then export LMOD_RC=${LMOD_RC:+$LMOD_RC:}$1; fi }
post_add_luarc /home/rpb/community-collections/cc_tools/lmodrc.lua
export MODULEPATH=${MODULEPATH:+$MODULEPATH:}/home/rpb/community-collections/modulefiles
source /home/rpb/community-collections/lmod/lmod/init/bash
export _COMCOL_ROOT="/home/rpb/community-collections"
post_add_luarc () { if [ -s "$1" ] && [[ ":$LMOD_RC:" != *":$1:"* ]]; then export LMOD_RC=${LMOD_RC:+$LMOD_RC:}$1; fi }
post_add_luarc /home/rpb/community-collections/cc_tools/lmodrc.lua
~~~

You can start using singularity by sourcing this script.

~~~
source /path/to/community-collections/profile_cc.sh
~~~

Now CC is ready for use. Skip to the [usage section](#usage) to continue.

Case 2: A minimal system without root
-------------------------------------

If you do not have root access on your machine, you can use Singularity if you have a kernel that provides uesr namespaces. You can install the code using the exact same procedure above, with only one difference. Your `cc.yaml` file will have a `sandbox` flag in the `singularity` entry. Set it if you lack root, and the code will use the `userns` and `sandbox` flags when building Singularity containers. These are described in the [Singularity documentation](https://sylabs.io/guides/3.3/user-guide/build_a_container.html). 

If your kernel does not provide usernamespaces, the code will refuse to build. A sandbox is really just a standard directory structure. The downside to using sandboxes is the large overhead caused by using many small files. This solution is nevertheless highly useful for users without root.


Case 3: An HPC resource with Singularity and Lmod
-------------------------------------------------

If you wish to use CC on a well-maintained HPC resource that already provides Singularity and Lmod, you can install it with the same procedure above. The code will detect these components and use the available versions instead of building its own.

~~~
git clone http://github.com/community-collections/community-collections
cd community-collections
./cc refresh
~~~

Note that you may need to run `module load singularity` beforehand to ensure that CC can find that program. It will use a separate alias module to access the singularity executable. The build procedure is very similar for the first two cases, however CC will rely on system-wide components (lua, tcl, etc) wherever possible. As with the previous cases, you can enable CC by preparing and sourcing a profile script with the following commands.

~~~
$ ./cc profile
[CC] [STATUS] reading cache.json
[CC] [STATUS] to use CC, run: source /home/rpb/community-collections/profile_cc.sh
[CC] [STATUS] proposed modifications to ~/.bashrc:
source /home/rpb/community-collections/profile_cc.sh
[QUESTION] okay to add the above to your ~/.bashrc? (y/N)?  
[CC] [STATUS] cache is unchanged
~~~

The `profile_cc.sh` script ([see above](#profile)) adds a new moduletree to Lmod and sets the correct environment variables to use singularity. You can start using singularity by sourcing this script.

~~~
source /path/to/community-collections/profile_cc.sh
~~~

<a name="usage"></a>
Usage
-----

Once CC is installed, it behaves almost exactly like a standard software module. The moduletree provided by CC will coeexist with your preexisting modules.

~~~
$ module avail
------------------- /home/rpb/community-collections/modulefiles -------------------
   R/3.6.0              (a)      julia/1.0.1 (a)    julia/1.1.0               (a)
   R/3.6.1              (a,D)    julia/1.0.2 (a)    julia/1.1.1               (r,D)
   cc/conda/default              julia/1.0.3 (a)    lolcow/latest             (a)
   cc/env/default                julia/1.0.4 (a)    tensorflow/1.12.3-gpu-py3 (g,a)
   cc/singularity/3.3.0          julia/1.1   (a)

  Where:
   g:  built for GPU
   r:  Downloaded  and ready to use (community collections).
   a:  Available for download (community collections).
   D:  Default Module

Use "module spider" to find all possible modules.
Use "module keyword key1 key2 ..." to search for all possible modules matching any of the "keys".
~~~

The modules prefixed with `cc` provide the Miniconda environment (`cc/env`) and conda itself (`cc/conda`) for internal use by CC. The `cc/singularity` module will point to either a detected Singularity already installed on the machine (which might be available from a separate module) or the internal copy built by CC. You do not have to use these modules directly.

The remaining modules are provided by the versions in the `cc.yaml` settings file. The property tag "(a)" indicates that they are ready to be downloaded, while `(r)` indicates that they have already been downloaded. When you load an "available" module for the first time, CC will call a `singularity pull` to download the image to `~/.cc_images`.

~~~
ml R
[CC] making a cache directory: /home/rpb/.cc_images
INFO:    Converting OCI blobs to SIF format
INFO:    Starting build...
Getting image source signatures
Copying blob sha256:23427ac613ac3b1217287fc64101680b8c27c7aaaf99228c376aee6231d02953
 48.05 MiB / 48.05 MiB [====================================================] 0s
Copying blob sha256:2ee18016dfa8b3bbdffb48a68b83c1d69193eac322d1978db9b6984cef885c1d
 1.80 KiB / 1.80 KiB [======================================================] 0s
Copying blob sha256:fb681ccd8fcdf49564df3c9789f60a37e443f99966342db1a34a898bb5e61375
 26.13 MiB / 26.13 MiB [====================================================] 0s
Copying blob sha256:ebbfe00354247f9c78ade5a97ce6a5947ea5121514fd0997ecef71853db7eb7a
 842.64 KiB / 842.64 KiB [==================================================] 0s
Copying blob sha256:5c8c1f2bdc1d29116d207c3682c7ad6f3335a7d92114c66d1a07ef8741833424
 295 B / 295 B [============================================================] 0s
Copying blob sha256:2bf2af8bf134f4b0d89b1088fc2fc30ecaa0842dbee79f7e2e8084f8e2fb6778
 192.58 MiB / 192.58 MiB [==================================================] 2s
Copying config sha256:09a59a224992641fdec61f2bd4ade7929e83ba1c3af1976d81251aea498e173f
 3.73 KiB / 3.73 KiB [======================================================] 0s
Writing manifest to image destination
Storing signatures
INFO:    Creating SIF file...
INFO:    Build complete: /home/rpb/.singularity/cache/oci-tmp/d0b534c18ca77cff083c681b234ddcd4e58b198412d307dbf27cb02f7aa413b0/r-base_3.6.1.sif
[CC] downloaded the image: /home/rpb/.cc_images/R-3.6.1.sif
[CC] checking image sizes at /home/rpb/.cc_images
   265MB R-3.6.1.sif
   265MB TOTAL
[CC] the ~/.singularity folder is also 520MB
[CC] you can clear the singularity cache with: "singularity cache clean -f"
[CC] please be mindful of your quota
[CC] the module is ready: R
~~~

The code reports the size of the image because it is downloaded to the `~/.cc_image` folder and may count against a quota. After loading the module once, the code is marked "ready" on the module list and the next time you load the module, it will used the cached image. Most programs, like `R` are aliased directly to a shell function that calls singularity to start the container with the `R` command. It also pipes arguments into that command. Aside from the output above, the use of a singularity container is completely opaque to the user.

Configuration
-------------

CC is designed to provide "versionless" modules from the fairly simple `cc.yaml` settings file. Let us consider the `R` package described above. The following is the default `cc.yaml` after we have installed the pacakge.

~~~
# cc.yaml
images: ~/.cc_images
lmod:
  root: ./lmod
module_settings:
  source: docker
singularity:
  path: ./singularity
  sandbox: false
whitelist:
  R:
    calls:
    - R
    - Rscript
    repo: r-base
    source: docker
    version: '>=3.6'
  julia:
    source: docker
    version: '>=1.0.1'
  lolcow:
    repo: leconte/examples/lolcow
    source: library
    version: latest
  tensorflow:
    calls:
    - python
    gpu: true
    repo: tensorflow/tensorflow
    shell: false
    source: docker
    version: 1.12.3-gpu-py3
~~~

**Versions** The `version` strings above allow you to include all versions after a certain point, however you can also serve a single, explicit version. When you use the greater-than operator e.g. `>=3.6`, Lmod will automatically load the latest version whenever you run e.g. `module load R`. To provide the latest versions, you can periodically run the `./cc refresh` command to update the module tree. This is preferable to the use of versions tagged "latest" from the source because it calls the docker API to check for an explicit version number.

**Sources** [DockerHub](https://hub.docker.com/) is the default source for the Singularity images, however this default is set in the `module_settings` section and can be changed. Nevertheless all modules in the example above explicitly cite their source in the recipe, which can be used to override the default. The `R` package above specifies DockerHub by using `source: docker`. Similarly, the `repo` flag allows the administrator to define the organization which provides a particular container.

**Shell functions** By default, the name of the section in the `whitelist` is mapped to a shell function that calls `singularity run` on the container. However, you can also add the `calls` section to provide either a list of additional shell function names, or a set of key-value pairs for mapping exterior shell functions (keys) to programs inside the container (values). You can disable the default mapping with `shell: false` to disable the use of a `tensorflow` shell function, since that program is invoked with `python` instead.

**GPU Compatibility** The `gpu` flag causes the program to use the [Nvidia bindings](https://docs.nvidia.com/ngc/ngc-user-guide/singularity.html) available in Singularity.

**Image locations** Note that we automatically save the images to `~/.cc_yaml` for each user, however this can be configured with the `~/.cc_images` command.

Blacklist
---------

Adding the following to your `cc.yaml` will exclude certain pacakges from the moduletree.

~~~
blacklist:
 - julia
 - qiime2
~~~

The names on this list will cause the `./cc refresh` loop to skip these modules (presumably named in the `whitelist`) when building the module tree.

Extensibility
-------------

The CC framework is designed to generate a large, dynamic set of modules based on the latest available versions of popular software packages provided by the container repositories. As a result, the successful deployment of CC depends almost entirely on the settings outlined in the `cc.yaml` file. We propose that these files can be shared between institutions to provide a portable means of publishing the software that they provide in containers for the users. Sites which build and push custom images to the repositories can also add these images easily to the `cc.yaml` file to allow their modules to reflect the diversity of packages that they have built for their users. In this way, the CC framework provides a simple way for HPC sites to coordinate and share a standardized list of preferred software, sources, versions, and even associated shell functions from among the many useful respository services.
