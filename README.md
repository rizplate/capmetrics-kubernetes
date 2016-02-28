# capmetrics-kubernetes

[![License](https://img.shields.io/dub/l/vibe-d.svg)](http://doge.mit-license.org)

Quick and dirty distributed data processing for CapMetrics on [Kubernetes](https://blog.redspread.com/2015/12/31/basic-kubernetes-vocabulary/).

## High-Level Overview

This project configures a Kubernetes cluster to setup a Redis server (deployed as a [pod](http://kubernetes.io/v1.1/docs/user-guide/pods.html)), and a bunch of dumb worker nodes (deployed using a [replication controller](http://kubernetes.io/v1.1/docs/user-guide/replication-controller.html)). Processing jobs are queued on Redis using the [RQ](https://github.com/nvie/rq) library, and the workers poll Redis for new jobs. When workers complete a job, they upload their results to S3. If a job fails or takes too long, it's put onto a `failed` queue to be checked and restarted later.

## Motivation

I've got about a year's worth of vehicle position data over on the CapMetrics repo that needs to be pre-processed before it can be aggregated. I make changes to the pre-processing code pretty often which means I need to re-process it all after every change before I can see the new aggregated stats. In terms of the data's space, it's small (< 5GB of CSV files, so Hadoop/Spark aren't worth it), but it takes about ~5 minutes to process a single day's worth of data.

Since I'm impatient, I don't want to process this all on a single machine, but since I'm lazy, I don't want to go through the trouble of manually distributing the processing across several machines.

Besides Kubernetes, there's nothing new or interesting. Kubernetes is just the easiest way to setup a Redis server and a bunch of workers inside Docker containers, connect them, and then tear them all down when I'm finished.

## TL;DR Usage

Assuming a Kubernetes cluster is available, and the Docker images for the worker and dashboard have been built, we can setup the job queue, workers, and dashboard with:

```
kubectl create -f kubernetes/img-pull-secret.yaml
kubectl create -f kubernetes/redis-pod.json
kubectl create -f kubernetes/redis-service.json
kubectl create -f kubernetes/worker-controller.json
kubectl create -f kubernetes/dashboard-controller.json
kubectl create -f kubernetes/dashboard-service.json
```

From here, we can use RQ to add jobs:

```python
from rq import Queue
from redis import StrictRedis

conn = StrictRedis(host='<KUBERNETES-NODE>', port=<NODE-PORT>)
q = Queue(connection=redis_conn)


import tasks
q.enqueue(tasks.process_day_to_s3, args=('2015-12-01', 's3-bucket', 's3-key'))
q.enqueue(tasks.process_day_to_s3, args=('2015-12-02', 's3-bucket', 's3-key'))
q.enqueue(tasks.process_day_to_s3, args=('2015-12-03', 's3-bucket', 's3-key'))

...

```


# Usage

1. Build the Docker images for the workers and monitoring dashboard.

  ```
  docker build -t worker-image -f Dockerfile.worker .
  docker build -t dashboard-image -f Dockerfile.dashboard .
  ```

2. Tag and push the Docker images to a registry. I used AWS's private Docker registry service (called [EC2 Container Registry](http://aws.amazon.com/ecr/) or ECR for short). Pushing images to ECR and configuring Kubernetes on how to access your ECR repos is a little tricky. Here's how it works:

    1. First, you'll need [authenticate your local Docker daemon with ECR](http://docs.aws.amazon.com/AmazonECR/latest/userguide/Registries.html#registry_auth).

    2. Then, [tag and push your Docker images to ECR](http://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html).

    3. Now any pod or replication controller that creates containers from images stored on ECR needs to know how to authenticate with ECR. You can do this by creating a [secret containing the auth info on how to authenticate with ECR](http://kubernetes.io/v1.0/docs/user-guide/images.html#specifying-imagepullsecrets-on-a-pod), and specifying that secret on each pod or RC that uses an image stored on ECR.

3. Start a Kubernetes cluster. [Google Container Engine](https://cloud.google.com/container-engine/) (GKE for short) provides fully-managed almost-one-click Kubernetes clusters. It's the easiest way to a Kubernetes cluster started.
  1. If you're a broke student like me and have some spare AWS credit, [bootstrapping a Kubernetes cluster on AWS](http://kubernetes.io/v1.1/docs/getting-started-guides/aws.html) is easier than you think.

4. Create the image pull secret. Any pod or RC that needs to authenticate with a private registry like ECR can use this secret to pull images.

    ```
    kubectl create -f kubernetes/img-pull-secret.yaml
    ```

5. Create the Redis [pod](http://kubernetes.io/v1.1/docs/user-guide/pods.html). The pod is defined from the Redis Docker image.

    ```
    kubectl create -f kubernetes/redis-pod.json
    ```

6. Create the Redis service. This makes the Redis pod available both within the cluster (via [DNS](http://kubernetes.io/v1.1/docs/user-guide/services.html#dns)), and outside the cluster. Specifically, the Redis service can be connected to from anywhere within the Redis pod's [namespace](http://kubernetes.io/v1.1/docs/user-guide/namespaces.html) in the cluster, for example, a client could connect using `redis-cli -h redis -p 6379`. Outside the cluster, any client can connect to the service over a [node port](http://kubernetes.io/v1.1/docs/user-guide/services.html#type-nodeport).

    ```
    kubectl create -f kubernetes/redis-service.json
    ```

7. Create the worker replication controller (or RC). This starts a couple of workers based from a single Docker image to process jobs from the queue on Redis.

    ```
    kubectl create -f kubernetes/worker-controller.json
    ```

8. Create the dashboard controller. This starts the dashboard web app for monitoring the status of workers and jobs in the queue.

    ```
    kubectl create -f kubernetes/dashboard-controller.json
    ```

9. Create the dashboard service. This makes the dashboard available outside the cluster (using a [node port](http://kubernetes.io/v1.1/docs/user-guide/services.html#type-nodeport)).

    ```
    kubectl create -f kubernetes/dashboard-service.json
    ```

Now with everything up and running we can add some jobs using RQ. First, we need to connect to the Redis server, which is available on a predetermined port on any node in the Kubernetes cluster thanks to the Redis service we setup earlier.


```python
from rq import Queue
from redis import StrictRedis

conn = StrictRedis(host='<KUBERNETES-NODE>', port=<NODE-PORT>)
q = Queue(connection=redis_conn)


import tasks
q.enqueue(tasks.process_day_to_s3, args=('2015-12-01', 's3-bucket', 's3-key'))
q.enqueue(tasks.process_day_to_s3, args=('2015-12-02', 's3-bucket', 's3-key'))
q.enqueue(tasks.process_day_to_s3, args=('2015-12-03', 's3-bucket', 's3-key'))

...

```