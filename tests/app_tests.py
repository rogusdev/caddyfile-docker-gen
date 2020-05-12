import unittest
from unittest.mock import Mock

from src.app import (
    GenerationConfig,
    ContainerConfig,
    DockerContainerConfigsFactory,
    CaddyfileFactory,
    CaddyfileDockerGenerator
)


CADDY_IMAGE = 'caddy'
LABEL_PREFIX = 'caddy'
CADDYFILE_PATH = '/etc/caddy/Caddyfile'


class TestDockerContainerConfigsFactory(unittest.TestCase):

    @staticmethod
    def _mock_container(image_tags = [], labels = {}, ip_address = None):
        mock_container = Mock()
        mock_container.image = Mock()
        mock_container.image.tags = image_tags
        mock_container.labels = labels
        if ip_address is not None:
            mock_container.attrs = {"NetworkSettings": {"Networks": {"TestNetwork": {"IPAddress": ip_address}}}}
        return mock_container

    @staticmethod
    def _mock_docker_client(containers = []):
        docker_client = Mock()
        docker_client.containers = Mock()
        docker_client.containers.list.return_value = containers
        return docker_client

    def test_get_container_configs_caddy_container(self):
        tag_tests = [
            ["simple", [CADDY_IMAGE], None],
            ["multiple", ["somethingelse", CADDY_IMAGE], None],
            ["tagged", [CADDY_IMAGE + ":someversion"], None],
            ["notfound", ["somethingelse", CADDY_IMAGE + "2"], "irrelevant_prefix"]
        ]
        for tag_test in tag_tests:
            msg, image_tags, label_prefix = tag_test
            with self.subTest(msg):
                docker_client = self._mock_docker_client(
                    [
                        self._mock_container(
                            image_tags = image_tags
                        )
                    ]
                )

                generation_config = GenerationConfig(CADDY_IMAGE, label_prefix, None)
                container_config_factory = DockerContainerConfigsFactory(docker_client, generation_config)
                caddy_container, _ = container_config_factory.get_container_configs()

                if label_prefix is None:
                    self.assertIsNotNone(caddy_container)
                else:
                    self.assertIsNone(caddy_container)

    def test_get_container_configs_container_configs(self):
        docker_client = self._mock_docker_client(
            [
                self._mock_container(
                    labels = {
                        LABEL_PREFIX: "hello.world.com",
                        f"{LABEL_PREFIX}.reverse_proxy": "$CONTAINER_IP:5000"
                    },
                    ip_address = "172.20.0.2"
                )
            ]
        )

        generation_config = GenerationConfig(None, LABEL_PREFIX, None)
        container_config_factory = DockerContainerConfigsFactory(docker_client, generation_config)
        _, container_configs = container_config_factory.get_container_configs()

        self.assertEqual(len(container_configs), 1)
        self.assertEqual(container_configs[0].ip, "172.20.0.2")
        self.assertEqual(
            container_configs[0].directive_nodes,
            [
                ["", "hello.world.com"],
                ["", "reverse_proxy", "$CONTAINER_IP:5000"]
            ]
        )


class TestCaddyfileFactory(unittest.TestCase):

    def test_generate_caddyfile(self):
        container_configs = [
            ContainerConfig(
                ip = '172.20.0.2',
                directive_nodes = [
                    ["","hello.world.com"],
                    ["","reverse_proxy", "$CONTAINER_IP:5000"]
                ]
            )
        ]

        caddyfile_factory = CaddyfileFactory()
        caddyfile_text = caddyfile_factory.generate_caddyfile(container_configs)

        self.assertEqual(caddyfile_text, """
hello.world.com {
    reverse_proxy 172.20.0.2:5000
}
""")


if __name__ == '__main__':
    unittest.main()
