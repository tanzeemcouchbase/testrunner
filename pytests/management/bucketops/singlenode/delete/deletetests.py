import unittest
import uuid
from TestInput import TestInputSingleton
import logger
import time
from membase.api.rest_client import RestConnection
from membase.helper.bucket_helper import BucketOperationHelper
from remote.remote_util import RemoteMachineShellConnection

log = logger.Logger.get_logger()

class DeleteMembaseBucketsTests(unittest.TestCase):

    servers = None
    input = None
    log = None

    def setUp(self):
        self.log = logger.Logger.get_logger()
        self.input = TestInputSingleton.input
        self.assertTrue(self.input, msg="input parameters missing...")
        self.servers = self.input.servers
        BucketOperationHelper.delete_all_buckets_or_assert(servers=self.servers, test_case=self)

    def tearDown(self):
        BucketOperationHelper.delete_all_buckets_or_assert(servers=self.servers, test_case=self)

    def test_default_on_11211(self):
        name = 'default'
        for serverInfo in self.servers:
            rest = RestConnection(serverInfo)
            rest.create_bucket(bucket=name,
                               ramQuotaMB=200,
                               replicaNumber=1,
                               proxyPort=11211)
            remote = RemoteMachineShellConnection(serverInfo)

            msg = 'create_bucket succeeded but bucket {0} does not exist'.format(name)
            self.assertTrue(BucketOperationHelper.wait_for_bucket_creation(name, rest), msg=msg)
            rest.delete_bucket(name)
            msg = 'bucket "{0}" was not deleted even after waiting for two minutes'.format(name)
            self.assertTrue(BucketOperationHelper.wait_for_bucket_deletion(name, rest, timeout_in_seconds=30), msg=msg)
            msg = 'bucket {0} data files are not deleted after bucket deleted from membase'.format(name)
            self.assertTrue(
                self.wait_for_data_files_deletion(name,
                                                  remote_connection=remote,
                                                  rest=rest, timeout_in_seconds=20), msg=msg)

    def test_non_default(self):
        name = 'new-bucket-{0}'.format(uuid.uuid4())
        for serverInfo in self.servers:
            rest = RestConnection(serverInfo)
            rest.create_bucket(bucket=name,
                               ramQuotaMB=200,
                               replicaNumber=1,
                               proxyPort=11211)
            remote = RemoteMachineShellConnection(serverInfo)
            msg = 'create_bucket succeeded but bucket {0} does not exist'.format(name)
            self.assertTrue(BucketOperationHelper.wait_for_bucket_creation(name, rest), msg=msg)
            rest.delete_bucket(name)
            msg = 'bucket "{0}" was not deleted even after waiting for 30 seconds'.format(name)
            self.assertTrue(BucketOperationHelper.wait_for_bucket_deletion(name, rest, timeout_in_seconds=30), msg=msg)
            msg = 'bucket {0} data files are not deleted after bucket deleted from membase'.format(name)
            self.assertTrue(
                self.wait_for_data_files_deletion(name,
                                                  remote_connection=remote,
                                                  rest=rest, timeout_in_seconds=20), msg=msg)


    #TODO: move these methods to a helper class
    def wait_for_data_files_deletion(self,
                                     bucket,
                                     remote_connection,
                                     rest,
                                     timeout_in_seconds=120):
        self.log.info('waiting for bucket data files deletion from the disk ....')
        start = time.time()
        while (time.time() - start) <= timeout_in_seconds:
            if self.verify_data_files_deletion(bucket, remote_connection, rest):
                return True
            else:
                data_file = '{0}-data'.format(bucket)
                self.log.info("still waiting for deletion of {0} ...".format(data_file))
                time.sleep(2)
        return False


    def verify_data_files_deletion(self,
                                   bucket,
                                   remote_connection,
                                   rest):
        node = rest.get_nodes_self()
        for item in node.storage:
            #get the path
            data_file = '{0}-data'.format(bucket)
            if remote_connection.file_exists(item.path, data_file):
                return False
        return True