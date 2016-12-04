# lambda-exec-wrapper
AWS Lambda handler that run any http-server and proxy http requests from Amazon API Gateway with Lambda Proxy Integration.
Running the http-server with chroot (fakechroot), there is no need to change the mainly configuration from ran in real server.

# example
## OpenResty
[OpenResty](http://openresty.org/) is "Turning Nginx into a Full-Fledged Scriptable Web Platform".

## making OpenResty fileset
If you use public repository, you can extract the OpenResty fileset using this commands.
Otherwise, put your fileset under "payload" as root directory.

```
(In plain Amazon Linux)
$ cd lambda-exec-wrapper
$ mkdir payload fakeroot work
$ sudo mount -t overlay overlay -o lowerdir=/,upperdir=payload,workdir=work fakeroot
$ sudo chroot fakeroot
$ yum install fakechroot-libs
$ ## (add OpenResty.repo file like CentOS6: http://openresty.org/en/linux-packages.html)
$ yum --disablerepo="*" --enablerepo="openresty" install --releasever=6 openresty
$ exit
$ sudo umount fakeroot
$ sudo rm -fr work fakeroot payload/{root,var,etc,tmp}

$ tree payload
payload
└── usr
    ├── bin
    │   └── openresty -> /usr/local/openresty/nginx/sbin/nginx
    ├── lib64
    │   └── fakechroot
    │       └── libfakechroot.so
    └── local
        └── openresty
            ├── bin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

## make payload.json
Lambda handler configuration.
In lambda, process has no root privileges, so we must change listen-port from tcp/80(or system-port).
The following is using an unix domain socket and mkdir for logfile and sockfile before execution.

```
{
  "fakechroot": {
    "rewrite": {
      "/usr/local/openresty/nginx/conf/.+\\.conf$": {
        "^\\s+listen\\s.*$": "listen unix:/usr/local/run/nginx.sock;"
      }
    },
    "symlink": [ "/dev" ]
  },
  # mkdir in fakeroot (if "fakechroot" directive exists)
  "mkdir": ["/usr/local/openresty/nginx/logs", "/usr/local/run"],
  "exec": "/usr/local/openresty/nginx/sbin/nginx",
  "connection": "unix:/usr/local/run/nginx.sock",

  # add request header
  "header": {
    "Host": "www.example.org"
  }
}
```

## zip
```
# zip -ry9 function.zip *
```

The lambda handler is "apigateway.lambda_handler".

