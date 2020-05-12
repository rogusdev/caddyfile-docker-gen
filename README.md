# caddyfile-docker-gen
Generate Caddyfile (for Caddy 2) from Docker containers and reload caddy in its (separate) docker container


docker-compose -f docker-compose-demo.yaml up --build -d

mkdir caddy_data

docker-compose up --build -d

docker-compose -f docker-compose-gen.yaml up --build -d

curl --unix-socket /var/run/docker.sock http://localhost/containers/json | jq


docker exec -it caddyfile-docker-gen_caddy_1 cat /etc/caddy/Caddyfile

docker exec -it caddyfile-docker-gen_caddy_1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile

# Cannot rm the Caddyfile file, must edit it in place!
#  https://github.com/moby/moby/issues/15793#issuecomment-135411504

docker-compose restart caddy



# let caddy docker network (-i) proxy requests to other docker webapp network (-o)
#  use docker network ls (also in ifconfig) to see the ids for each br(idge) network
#  by default, docker compose networks are named "{compose yaml folder}_default"
# https://stackoverflow.com/questions/36035595/communicating-between-docker-containers-in-different-networks-on-the-same-host/51373066#51373066
sudo iptables -I DOCKER-USER -i br-XXCADDYNETXX -o br-YYWEBAPPNETYY -j ACCEPT


docker exec -it caddyfile-docker-gen_caddy_1 apk --no-cache add curl

docker exec -it caddyfile-docker-gen_caddy_1 curl http://172.19.0.2:80



$ curl https://localhost
curl: (60) SSL certificate problem: unable to get local issuer certificate
More details here: https://curl.haxx.se/docs/sslcerts.html

curl failed to verify the legitimacy of the server and therefore could not
establish a secure connection to it. To learn more about this situation and
how to fix it, please visit the web page mentioned above.

$ curl https://whoami1.example.com
I'm 93ba9a067d58
$ curl https://whoami2.example.com
I'm 430e7af4b292

$ curl http://172.20.0.3:8000
I'm 93ba9a067d58
$ curl http://172.20.0.2:8000
I'm 430e7af4b292


# Run tests
In fish:

    docker build -t caddyfile-docker-gen . ; and docker run -it caddyfile-docker-gen -m unittest tests.app_tests
