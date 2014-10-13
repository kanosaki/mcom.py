mcom.py -- Simple multi network casting tool and library
========================================================

Multi method message casting command line tool and library.

Current implementation status
-----------------------------
* Message type
    - JSON
* Casting method
    - Multicasting
        - IPv4
        - IPv6 (not yet)
    - Unicasting (not yet)
    - Broadcasting (not yet)
* Operating System
    - Mac OS X
    - Linux (not tested)
    - Windows (not tested)

    
CLI Usage
---------
* Send a message to `address`

```sh
echo '{"msg": "HELLO!"}' | python mcom.py <address> 
```

* Listen messages

```sh
python mcom.py -l <address> 
```

Requirements
-------------
* Python 2.7 or above

Important Notice
-----------------
* All messages will be compressed by gzip before casting.
* Compressed message size is currently limited to 1024bytes.
* Messages will be sent thru UDP, so it might be dropped, there is guarantee of delivery, ordering, or duplicate protection.
