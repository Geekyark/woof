import threading, logging, time, signal

from kafka import KafkaConsumer
from kafka.common import LeaderNotAvailableError,KafkaUnavailableError

log = logging.getLogger("kafka")

class FeedConsumer(threading.Thread):
    """Threaded gomsg feed consumer
    callbacks are called on a separate thread in the same method
    
    keyword arguments :

    broker (list): List of initial broker nodes the consumer should contact to
    bootstrap initial cluster metadata.  This does not have to be the full node list.
    It just needs to have at least one broker

    group (str): the name of the consumer group to join, Offsets are fetched /
    committed to this group name.

    offset='smallest' : read all msgs from beginning of time;  default read fresh

    commit_every_t_ms:  How much time (in milliseconds) to before commit to zookeeper


    """
    daemon = True

    def __init__(self, broker, group, offset='largest', commit_every_t_ms=1000,
                 parts=None, kill_signal=signal.SIGTERM):
        self.brokerurl = broker
        self.kill_signal = kill_signal
        self.exit_consumer = False
        self.create_kill_signal_handler()
        try:
            self.cons = KafkaConsumer(bootstrap_servers=broker,
                                      auto_offset_reset=offset,
                                      auto_commit_enable=True,
                                      auto_commit_interval_ms=commit_every_t_ms,
                                      group_id=group
                                      )
        except KafkaUnavailableError:
            log.critical( "\nCluster Unavailable %s : Check broker string\n", broker)
            raise
        except:
            raise

        self.topics = []
        self.callbacks = {}
        super(FeedConsumer, self).__init__()

    def add_topic(self, topic, todo, parts=None):
        """
        Set the topic/partitions to consume

        todo (callable) : callback for the topic
        NOTE: Callback is for entire topic, if you call this for multiple
        partitions for same topic with diff callbacks, only the last callback
        is retained

        topic : topic to listen to

        parts (list) : tuple of the partitions to listen to

        """
        self.callbacks[topic] = todo

        if parts is None:
            log.info(" FeedConsumer : adding topic %s ", topic)
            self.topics.append(topic)
        else:
              for part in parts:
                  log.info(" FeedConsumer : adding topic %s %s", topic , part)
                  self.topics.append((topic,part))

        self.cons._client.ensure_topic_exists(topic)
        self.cons.set_topic_partitions(*self.topics)

    def remove_topic(self, topic,  parts=None):
        try:
            if parts is None:
                self.topics.remove(topic)
            else:
                for part in parts:
                    self.topics.remove((topic,part))
        except:
            log.critical("FeedConsumer : no such topic %s", topic)
            return
        log.info(" FeedConsumer : removed topic %s", topic)
        self.cons.set_topic_partitions(*self.topics)

    def create_kill_signal_handler(self):

        def set_stop_signal(signal, frame):
            self.exit_consumer = True

        signal.signal(self.kill_signal, set_stop_signal)

    def check_for_exit_criteria(self):
        if self.exit_consumer:
            self.cons.commit()
            exit(0)

    def run(self):
        while True:
            try:
                for m in self.cons.fetch_messages():
                    self.callbacks[m.topic](m.key, m.value)
                    self.cons.task_done(m)
                    # uncomment for consumer to work safely
                    #self.cons.commit()
                    self.check_for_exit_criteria()
                self.check_for_exit_criteria()
            except:
                time.sleep(1)
                continue

