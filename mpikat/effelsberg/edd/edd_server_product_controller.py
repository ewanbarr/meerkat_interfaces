import logging
import json
from tornado.gen import Return, coroutine
from katcp import Sensor, Message, KATCPClientResource
from mpikat.core.product_controller import ProductController, state_change

log = logging.getLogger("mpikat.edd_server_product_controller")


class EddServerProductController(ProductController):
    """
    """

    def __init__(self, parent, product_id, address, port):
        """
        @brief      Construct new instance

        @param      parent            The parent EddRoach2MasterController instance
        @param      product_id        A unique identifier for this product
        @param      r2rm_addr         The address of the R2RM (ROACH2 resource manager) to be
                                      used by this product. Passed in tuple format,
                                      e.g. ("127.0.0.1", 5000)
        """
        ProductController.__init__(self, parent, product_id)
        log.debug("Adress {}, {}".format(address, port))
        self._client = KATCPClientResource(dict(
            name="server-client_{}".format(product_id),
            address=(address, int(port)),
            controlled=True))
        self.__product_id = product_id
        self._client.start()

    def setup_sensors(self):
        """
        @brief    Setup the default KATCP sensors.

        @note     As this call is made only upon an EDD product configure call a mass inform
                  is required to let connected clients know that the proxy interface has
                  changed.
        """
        ProductController.setup_sensors(self)
        self._dummy_sensor = Sensor.string(
            "dummy-sensor",
            description="dummy sensor as alpha version of code",
            default="ALPHA VERSION OF CODE, NO MORE SENSORS HERE",
            initial_status=Sensor.UNKNOWN)
        self.add_sensor(self._dummy_sensor)
        self._parent.mass_inform(Message.inform('interface-changed'))

    @coroutine
    def _safe_request(self, request_name, *args, **kwargs):
        log.info("Sending request '{}' with arguments {}".format(request_name, args))
        yield self._client.until_synced()
        response = yield self._client.req[request_name](*args, **kwargs)
        if not response.reply.reply_ok():
            log.error("'{}' request failed with error: {}".format(request_name, response.reply.arguments[1]))
            raise RuntimeError(response.reply.arguments[1])
        else:
            log.debug("'{}' request successful".format(request_name))
            raise Return(response)

    @coroutine
    def deconfigure(self):
        """
        @brief      Deconfigure the product

        @detail     This method will remove any product sensors that were added to the
                    parent master controller.
        """
        yield self._safe_request('deconfigure')

    @coroutine
    def configure(self, config):
        """
        @brief      A no-op method for supporting the product controller interface.
        """
        logging.debug("Send cfg to {}".format(self.__product_id))
        yield self._safe_request("configure", json.dumps(config), timeout=120.0)

    @coroutine
    def capture_start(self):
        """
        @brief      A no-op method for supporting the product controller interface.
        """
        self._safe_request("capture_start")

    @coroutine
    def capture_stop(self):
        """
        @brief      A no-op method for supporting the product controller interface.
        """
        self._safe_request("capture_stop")
