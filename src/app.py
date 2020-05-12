import os
import docker


class GenerationConfig:
    def __init__(self, caddy_image, label_prefix, caddyfile_path):
        self.caddy_image = caddy_image
        self.label_prefix = label_prefix
        self.caddyfile_path = caddyfile_path


class GenerationConfigFromEnvVars:
    ENV_VAR_CADDY_IMAGE = 'CADDY_IMAGE'
    ENV_VAR_LABEL_PREFIX = 'LABEL_PREFIX'
    ENV_VAR_CADDYFILE_PATH = 'CADDYFILE_PATH'

    CADDY_IMAGE_DEFAULT = 'caddy'
    LABEL_PREFIX_DEFAULT = 'caddy'
    CADDYFILE_PATH_DEFAULT = '/etc/caddy/Caddyfile'

    @classmethod
    def from_env(cls):
        return GenerationConfig(
            caddy_image = os.environ.get(cls.ENV_VAR_CADDY_IMAGE, cls.CADDY_IMAGE_DEFAULT),
            label_prefix = os.environ.get(cls.ENV_VAR_LABEL_PREFIX, cls.LABEL_PREFIX_DEFAULT),
            caddyfile_path = os.environ.get(cls.ENV_VAR_CADDYFILE_PATH, cls.CADDYFILE_PATH_DEFAULT)
        )


class ContainerConfig:
    def __init__(self, ip, directive_nodes):
        self.ip = ip
        self.directive_nodes = directive_nodes


class DockerContainerConfigsFactory:
    def __init__(self, docker_client, generation_config):
        self.docker_client = docker_client
        self.generation_config = generation_config

    def get_container_configs(self):
        caddy_container = None
        container_configs = []

        # https://docs.docker.com/engine/api/sdk/examples/#list-and-manage-containers
        # https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.Container.attrs

        for container in self.docker_client.containers.list():
            image_tags = list(map(lambda tag: tag.split(':')[0], container.image.tags))
            if self.generation_config.caddy_image in image_tags:
                caddy_container = container
            else:
                directive_nodes = self._parse_labels_as_directives(container)
                if len(directive_nodes) > 0:
                    container_configs.append(
                        ContainerConfig(
                            DockerContainerConfigsFactory._container_ip(container),
                            directive_nodes
                        )
                    )

        return caddy_container, container_configs

    # https://github.com/nginx-proxy/nginx-proxy/blob/a28571765744b6523aea629efc8f657a5fa2c8ef/test/conftest.py#L140
    @staticmethod
    def _container_ip(container):
        net_info = container.attrs["NetworkSettings"]["Networks"]
        if "bridge" in net_info:
            return net_info["bridge"]["IPAddress"]

        # not default bridge network, fallback on first network defined
        network_name = next(iter(net_info))
        return net_info[network_name]["IPAddress"]

    @staticmethod
    def _parse_label_suffix(suffix, value):
        # root = {}
        # node = root
        # directives = suffix.split('.')
        # for directive in directives[:-1]:
        #     node[directive] = {}
        #     node = node[directive]
        # node[directives[-1]] = value
        # return root
        directives = suffix.split('.')
        directives.append(value)
        return directives

    def _parse_labels_as_directives(self, container):
        subprefix = self.generation_config.label_prefix + "."
        skip_len = len(self.generation_config.label_prefix)
        directive_nodes = []
        for label_key in container.labels:
            value = container.labels[label_key]
            if label_key == self.generation_config.label_prefix or \
                    label_key.startswith(subprefix):
                directive_nodes.append(
                    DockerContainerConfigsFactory._parse_label_suffix(
                        label_key[skip_len:],
                        value
                    )
                )
        return directive_nodes


class CaddyfileFactory:
    def generate_caddyfile(self, container_configs):
        return "\n".join([
            self._caddyfile_domain(container_config)
            for container_config in container_configs
        ])

    def _caddyfile_domain(self, container_config):
        # TODO: flesh this out
        # FIXME: how to combine directives together, by each layer?
        # TODO: allow for explicitly isolating repeated directives with *X for integer X, possibly with leading zeroes
        container_config.directive_nodes[1][2] = container_config.directive_nodes[1][2].replace("$CONTAINER_IP", container_config.ip)
        return f"\n{container_config.directive_nodes[0][1]} {{\n    {container_config.directive_nodes[1][1]} {container_config.directive_nodes[1][2]}\n}}\n"


class CaddyfileDockerGenerator:
    def __init__(self, docker_client, generation_config, container_config_factory, caddyfile_factory):
        self.docker_client = docker_client
        self.generation_config = generation_config
        self.container_config_factory = container_config_factory
        self.caddyfile_factory = caddyfile_factory

    def update_caddyfile(self):
        print(f"Updating Caddyfile")
        caddy_container, container_configs = self.container_config_factory.get_container_configs()
        # TODO: check if any diff exists to justify writing updated file
        caddyfile_text = self.caddyfile_factory.generate_caddyfile(container_configs)
        self._write_caddyfile(caddyfile_text)
        self._reload_caddy(caddy_container)

    def _write_caddyfile(self, caddyfile_text):
        f = open(self.generation_config.caddyfile_path, "w")
        f.write(caddyfile_text)
        f.close()

    def _reload_caddy(self, caddy_container):
        if caddy_container is not None:
            # https://caddyserver.com/docs/command-line#caddy-reload
            cmd = f"caddy reload --config {self.generation_config.caddyfile_path} --adapter caddyfile"
            print(f"Reloading Caddy with: '{cmd}'")
            caddy_container.exec_run(cmd)
        else:
            print("No caddy container to reload with updated Caddyfile!")


if __name__ == '__main__':
    docker_client = docker.from_env()
    generation_config = GenerationConfigFromEnvVars.from_env()
    container_config_factory = DockerContainerConfigsFactory(docker_client, generation_config)
    caddyfile_factory = CaddyfileFactory()
    generator = CaddyfileDockerGenerator(
        docker_client,
        generation_config,
        container_config_factory,
        caddyfile_factory
    )

    generator.update_caddyfile()
    # TODO: theoretically an update could come in on this sliver of a line
    #  between the snapshot to first event update and we would miss it
    #  ... meh, for now.
    # https://docker-py.readthedocs.io/en/stable/client.html#docker.client.DockerClient.events
    # for event in docker_client.events():
    #     generator.update_caddyfile()
    print('caddyfile-docker-gen interrupted! Terminated')
