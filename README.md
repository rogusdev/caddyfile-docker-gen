# caddyfile-docker-gen
Generate Caddyfile (for Caddy 2) from Docker containers and reload caddy in its (separate) docker container


```
# after starting a new docker container on the server, in the correct network, with the necessary labels
#  for now, need to rebuild caddyfile and restart caddy2
cd ~/caddyfile-docker-gen/
sudo chown -Rh $USER:$USER caddy_data/
docker-compose -f docker-compose-gen.yaml up --build -d
cd -


docker rm -f caddy
docker run -d --restart=always -p 80:80 -p 443:443 --network=www -v ./Caddyfile:/etc/caddy/Caddyfile:ro -v ./caddy_data:/data --name caddy caddy:2.1.1-alpine

docker rm -f caddyfile-docker-gen
docker build -t caddyfile-docker-gen . && docker run -d --restart=always --network=www -v /var/run/docker.sock:/var/run/docker.sock:ro -v ./Caddyfile:/etc/caddy/Caddyfile -e CADDY_IMAGE=caddy -e LABEL_PREFIX=caddy -e CADDYFILE_PATH=/etc/caddy/Caddyfile --name caddyfile-docker-gen caddyfile-docker-gen



# root writes the files so have to do this every time I docker-compose back up...
sudo chown -Rh $USER:$USER caddy_data/


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



# let caddy docker network (caddy) proxy requests to other docker webapp network (www)
#  use docker network ls (also in ifconfig) to see the ids for each br(idge) network
#  by default, docker compose networks are named "{compose yaml folder}_default"
# https://stackoverflow.com/questions/36035595/communicating-between-docker-containers-in-different-networks-on-the-same-host/51373066#51373066


docker network create www

WWW_BRIDGE_ID=$(docker network ls | grep www | cut -d ' ' -f 1)
CADDY_BRIDGE_ID=$(docker network ls | grep caddy | cut -d ' ' -f 1)

echo "caddy: $CADDY_BRIDGE_ID -- www: $WWW_BRIDGE_ID"
sudo iptables -I DOCKER-USER -i br-$CADDY_BRIDGE_ID -o br-$WWW_BRIDGE_ID -j ACCEPT
sudo iptables -I DOCKER-USER -i br-$WWW_BRIDGE_ID -o br-$CADDY_BRIDGE_ID -j ACCEPT
sudo iptables -L DOCKER-USER -v # to confirm




docker exec -it caddyfile-docker-gen_caddy_1 apk --no-cache add curl

docker exec -it caddyfile-docker-gen_caddy_1 curl http://172.19.0.2:80

docker exec -it caddyfile-docker-gen_caddy_1 curl http://172.21.0.2:5000/api/v1/hello



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
```

# Run tests
In fish:

    docker build -t caddyfile-docker-gen . ; and docker run -it caddyfile-docker-gen -m unittest tests.app_tests



    docker run --restart=always --network=caddy -u=$(id -u) -p 80:80 -p 443:443 -v ./Caddyfile:/etc/caddy/Caddyfile:ro -v ./caddy_data:/data --name caddy caddy:2.0.0-alpine

