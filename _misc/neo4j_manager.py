from graphdatascience import GraphDataScience
import yaml


class Neo4jDatabase:
    def __init__(self):
        config = self.load_config("settings/database.yml")

        self._NEO4J_DATABASE = config['NEO4J_DATABASE']

        self._gds = GraphDataScience(
            config['NEO4J_URI'],
            auth=(config['NEO4J_USER'], config['NEO4J_PASSWORD'])
        )


    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            return yaml.safe_load(file)

    def get_version(self):
        return self._gds.version()


if __name__ == '__main__':
    gds_instance = Neo4jDatabase()

    print(gds_instance.get_version())
    assert gds_instance.get_version()
