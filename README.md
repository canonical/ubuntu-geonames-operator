# Ubuntu Geonames Operator

**Ubuntu Geonames Operator** is a [charm](https://juju.is/charms-architecture)
that provides a geoname lookup service.

The service exposes an HTTP endpoint for querying timezones and geodata.

## Behavior

- Downloads and imports geodata into a local Sphinx Search and PostgreSQL database.
- Exposes an API over HTTP (using Apache and WSGI) on port 80.
- Supports ingress routing via the `traefik_k8s` relation.

## Basic usage

```bash
juju deploy ubuntu-geonames
```

Once the charm is deployed, you can check the status with Juju status:

```bash
❯ $ juju status
Model        Controller  Cloud/Region         Version  SLA          Timestamp
welcome-lxd  concierge-lxd  localhost/localhost  3.6.21   unsupported  11:47:41Z

App              Version  Status  Scale  Charm            Channel  Rev  Exposed  Message
ubuntu-geonames           active      1  ubuntu-geonames             1  no

Unit                Workload  Agent  Machine  Public address  Ports   Message
ubuntu-geonames/0*  active    idle   1        10.173.62.226   80/tcp  Done!

Machine  State    Address        Inst id        Base          AZ            Message
1        started  10.173.62.226  juju-e37332-2  ubuntu@24.04  juju-sandbox  Running
```

On first start up, the charm will set up the Postgres database, import the Geonames dataset, configure Sphinx Search, and start the Apache web server.

Change log level if needed:

```bash
juju config ubuntu-geonames log-level=debug
```

## Service inspection

```bash
systemctl status apache2.service
systemctl status postgresql.service
systemctl status sphinxsearch.service
journalctl -u apache2.service
```

## Testing

For information on tests and development workflows, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Ubuntu Geonames Operator is released under the [GPL-3.0 license](LICENSE).
