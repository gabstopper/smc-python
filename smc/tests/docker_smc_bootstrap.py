"""
Used to bootstrap the SMC into a docker container. Provides a clean installed version
with pre-existing license with SMC API enabled. All ports are forwarded from the native
docker host to the private SMC address, including Web Start.

In this configuration, docker is installed on CentOS7 (which uses systemd)
To enable docker remote API. http://sudoall.com/docker-remote-api-on-centos/
Modify: /usr/lib/systemd/system/docker.service; add the "ExecStart" entry to enable the
socket listen on the host:

[Service]
Type=notify
# the default is not to use systemd for cgroups because the delegate issues still
# exists and systemd currently does not support the cgroup feature set required
# for containers run by docker
#ExecStart=/usr/bin/dockerd
ExecStart=
ExecStart=/usr/bin/dockerd -H tcp://0.0.0.0:4243 -H unix:///var/run/docker.sock

systemctl start docker
"""
import sys
import json
import time
import requests


class DockerFailure(Exception):
    pass


# Represents SMC configuration and required ports. This can be done from the docker
# binary by running:
# docker run -d -p 8902-8918:8902-8918 -p 8082:8082 --network=mynet --ip=172.32.0.10 \
# --name smc_container dwlepage70/smc:v6.1
smc = {'HostConfig': {
    'NetworkMode': 'mynet',
    'PortBindings': {
        '8082/tcp': [{'HostPort': '8082'}],
        '8902/tcp': [{'HostPort': '8902'}],
        '8903/tcp': [{'HostPort': '8903'}],
        '8904/tcp': [{'HostPort': '8904'}],
        '8905/tcp': [{'HostPort': '8905'}],
        '8906/tcp': [{'HostPort': '8906'}],
        '8907/tcp': [{'HostPort': '8907'}],
        '8908/tcp': [{'HostPort': '8908'}],
        '8909/tcp': [{'HostPort': '8909'}],
        '8910/tcp': [{'HostPort': '8910'}],
        '8911/tcp': [{'HostPort': '8911'}],
        '8912/tcp': [{'HostPort': '8912'}],
        '8913/tcp': [{'HostPort': '8913'}],
        '8914/tcp': [{'HostPort': '8914'}],
        '8915/tcp': [{'HostPort': '8915'}],
        '8916/tcp': [{'HostPort': '8916'}],
        '8917/tcp': [{'HostPort': '8917'}],
        '8918/tcp': [{'HostPort': '8918'}]}, },
       'Image': 'dwlepage70/smc:v6.3.3',

       'Labels': {},
       'Mounts': [],
       'NetworkingConfig': {
    'EndpointsConfig': {
                'mynet': {
                    'IPAMConfig': {
                        'IPv4Address': '172.32.0.10'},
                }
    }
},
    'Config': {'ExposedPorts': {
        '22/tcp': {},
        '8082/tcp': {},
        '8902/tcp': {},
        '8903/tcp': {},
        '8904/tcp': {},
        '8905/tcp': {},
        '8906/tcp': {},
        '8907/tcp': {},
        '8908/tcp': {},
        '8909/tcp': {},
        '8910/tcp': {},
        '8911/tcp': {},
        '8912/tcp': {},
        '8913/tcp': {},
        '8914/tcp': {},
        '8915/tcp': {},
        '8916/tcp': {},
        '8917/tcp': {},
        '8918/tcp': {}}}}

# Network used for SMC host machine. Can be pre-created as well using docker binary:
# docker network create --subnet=172.32.0.0/24 mynet
mynet = {
    "Name": "mynet",
    "Scope": "local",
    "Driver": "bridge",
    "EnableIPv6": False,
    "IPAM": {
            "Driver": "default",
            "Options": {},
            "Config": [
                {
                    "Subnet": "172.32.0.0/24",
                    "Gateway": "172.32.0.1"
                }
            ]
    },
    "Internal": False,
    "Options": {},
    "Labels": {}}


def get_containers(all=True):  # @ReservedAssignment
    """
    Get all containers

    :param bool all: show all containers; otherwise only
           running containers are shown
    """
    response = do_get('containers/json', params={'all': all})
    if response.status_code == 200:
        return json.loads(response.text)


def get_containers_by_image(name):
    containers = get_containers()
    return [ids for ids in containers if ids.get('Image').startswith(name)]


def get_container_stats(container_id, stream=False):
    """
    Get stats from within container. 

    :param bool stream: stay connected to gather stats as stream (True)
           or connect once and disconnect (False)
    """
    response = do_get('containers/{}/stats'.format(container_id),
                      params={'stream': stream})
    return json.loads(response.text)


def get_images(limit=False, filter=None):  # @ReservedAssignment
    """
    Get images

    :param bool limit: True or False
    :param str filter: only return images with the specified name
    """
    response = do_get('images/json', params={'all': limit,
                                             'filter': filter})
    return json.loads(response.text)


def exec_create(container_id):
    """
    Creates an exec command string to run inside the specified container
    """
    cmd = {'AttachStdin': False,
           'AttachStdout': True,
           'AttachStderr': False,
           'Tty': False,
           'Cmd': ["/bin/sh", "-c", "/etc/init.d/sgMgtServer start && "
                   "/etc/init.d/sgLogServer start"]}

    response = do_post('containers/{}/exec'.format(container_id), payload=cmd)
    if response.status_code == 201:
        return json.loads(response.text).get('Id')
    else:
        raise DockerFailure(response.text)


def exec_start(exec_id):
    """
    Starts the exec command string created using exec_create
    """
    cmd = {'Detach': True,
           'Tty': False}

    response = do_post('exec/{}/start'.format(exec_id), payload=cmd)
    if response.status_code != 200:
        raise DockerFailure(response.text)
    return response


def exec_inspect(exec_id):
    """
    Inspect the running exec
    """
    response = do_get('exec/{}/json'.format(exec_id))
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        raise DockerFailure('Failed inspecting exec: %s' % response.text)


def create_container(name):
    """
    Create the container
    """
    response = do_post('containers/create', payload=smc, params={'name': name})
    if response.status_code == 201:
        return json.loads(response.text).get('Id')
    else:
        raise DockerFailure(json.loads(response.text))


def create_network():
    #POST /networks/create
    pass


def start_container(container_id):
    """ 
    Start the created container by id
    """
    response = do_post('containers/{}/start'.format(container_id))
    if response.status_code != 204:
        raise DockerFailure(json.loads(response.text))


def stop_container(container_id, wait=5):
    """
    Stop container
    """
    response = do_post('containers/{}/stop?t={}'.format(container_id, wait))
    if response.status_code != 204:
        raise DockerFailure('Failed to stop container: %s' % response.text)


def remove_container(container_id, volumes=True):
    """
    Remove container

    :param bool volumes: remove the volumes associated to the container
    """
    response = do_delete('containers/{}?v={}'.format(container_id, volumes))
    if not response.status_code == 204:
        raise DockerFailure('Failed removing container: %s' % response.text)


def do_post(uri, payload=None, params=None):
    response = requests.post('{}/{}'.format(docker_engine, uri),
                             data=json.dumps(payload),
                             params=params,
                             headers={'content-type': 'application/json'})
    return response


def do_get(uri, params=None):
    return requests.get('{}/{}'.format(docker_engine, uri),
                        headers={'content-type': 'application/json'},
                        params=params)


def do_delete(uri):
    return requests.delete('{}/{}'.format(docker_engine, uri))


if __name__ == '__main__':

    docker_engine = 'http://172.18.1.26:4243'

    if len(sys.argv[1:]) > 0:
        # docker_smc_bootstrap.py docker_host smc_version
        print("Got some args")

    # pprint(get_images())

    # for image in get_containers_by_image('dwlepage'):
    #    print("image: %s" % image)
    #    pprint(get_container_stats(image.get('Id')))

    for container in get_containers():
        if container.get('Image').startswith('dwlepage70/smc'):
            container_id = container.get('Id')
            print("Kill container: %s" % container_id)
            if container.get('State').lower() == 'running':
                stop_container(container_id)
            remove_container(container_id)

    container_id = create_container('smc_container')
    print("Created container id: %s" % container_id)

    for i in range(3):
        try:
            start_container(container_id)
        except DockerFailure as e:
            if e.message.get('message').startswith('invalid header field value "oci runtime error: container_linux.go'):
                print("Invalid header error, retry: %s" % i)
                time.sleep(2)
        else:
            break
        
    exec_id = exec_create(container_id)
    start = exec_start(exec_id)

    # Loop over running exec process waiting for return
    print("Executed startup, monitoring status..")
    while True:
        response = exec_inspect(exec_id)
        if response.get('Running'):
            time.sleep(5)
        else:
            if response.get('ExitCode') == 0:
                print("Completed command successfully, running image: %s" % smc['Image'])
            else:
                print("Command failed: %s" % response)
            break
