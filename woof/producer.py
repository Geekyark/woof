import logging, time

from kafka import KafkaProducer
from kafka.errors import KafkaTimeoutError
from .transactions import make_kafka_safe
from common import CURRENT_PROD_BROKER_VERSION
log = logging.getLogger("kafka")


class FeedProducer():
    """
    Feed Producer class
    use send() to send to any topic
    """

    def __init__(self, broker, retries=3, async=False):
        try:
            self.prod = KafkaProducer(bootstrap_servers=broker,
                                      key_serializer=make_kafka_safe,
                                      value_serializer=make_kafka_safe,
                                      retries=retries,
                                      api_version=CURRENT_PROD_BROKER_VERSION)
            self.async = async
        except Exception as e:
            log.error("[feedproducer log] Constructor error ERROR %s  /n",
                      str(e))
            raise

    def send(self, topic, *msgs):
        try:
            for msg in msgs:
                self.prod.send(topic, msg)
            log.debug("[feedproducer log] about to flush.. topic %s msg %s /n",
                      topic, str(msgs))

            if not self.async:
                self.prod.flush()
        except KafkaTimeoutError as e:
            log.error(
                "[feedproducer log] KafkaTimeoutError err %s topic %s  /n",
                str(e), topic)
            raise e
        except Exception as e1:
            log.error("[feedproducer log] GEN  err %s topic %s /n", str(e1),
                      topic)
            raise e1

    def flush(self):
        try:
            self.prod.flush()
        except KafkaTimeoutError as e:
            log.error(
                "[feedproducer log] KafkaTimeoutError err %s topic %s  /n",
                str(e), topic)
            raise e
        except Exception as e1:
            log.error("[feedproducer log] GEN  err %s topic %s /n", str(e1),
                      topic)
            raise e1
