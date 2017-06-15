
============
 ECX Client
============

This project aims to build a Python client for Catalogic Software's 
`ECX <https://catalogicsoftware.com/products/ecx/>`_ product. 

This repo holds two components. 

- An SDK that can be used by anyone interested in integrating ECX
  operations in their workflow.

- A command line utility with which ECX operations can be performed.

Installation
============

::

$ pip install ecxclient

Usage
=====

::

    $ ecxcli --help
    
    # This connects to ECX on localhost.
    $ ecxcli --user admin --passwd <PASSWORD> job list
    
    # To connect to a different host. Default user is "admin".
    $ ecxcli --url https://1.2.3.4:8443 --passwd <PASSWORD> job list
    
Notes
=====

- After a successful login, the command "remembers" the login session
  so there is no need to pass user name and password with every
  run.

Known Issues
============

- When "https" URL is used, there are some warnings displayed on the
  console. We need to find a way to get rid of them.
