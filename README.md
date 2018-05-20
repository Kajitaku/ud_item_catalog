# ud_item_catalog
Source code for Item Catalog Application

**You can CRUD Catalog Item with OAuth.

# Install following tools.
**Virtual Machine**
1. [vagrant](https://www.vagrantup.com/)
2. [virtualbox](https://www.virtualbox.org/wiki/Download_Old_Builds_5_1) (ver 5.1)

**Git**
If you don't already have Git installed, download Git from [git-scm.com](https://git-scm.com/downloads)

# Set up
**Virtual Machine**
1. `git clone https://github.com/udacity/fullstack-nanodegree-vm.git` to get virtual machine environment.
2. `cd fullstack-nanodegree-vm/vagrant`
3. `vagrant up` to lunch a virtual machine.

**Source code**
1. `cd ./fullstack-nanodegree-vm/vagrant/catalog`
2. `git clone https://github.com/Kajitaku/ud_item_catalog.git` to get source code.

**Database**
1. `cd ./fullstack-nanodegree-vm/vagrant/`
2. `vagrant ssh`
3. `cd /vagrant/catalog/ud_item_catalog`
4. `python database_setup.py` to set up database structure.
5. `python lotsofmenus.py` to add database data.


# How to use
1. `cd ./fullstack-nanodegree-vm/vagrant/`
2. `vagrant up`
3. `vagrant ssh`
4. `cd /vagrant/catalog/ud_item_catalog/`
5. `python project.py`

# License
MIT
