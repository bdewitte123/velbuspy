import sanic.response
import sanic.request

from typing import Any, Callable

from .VelbusModule import VelbusModule
from ..VelbusProtocol import VelbusProtocol
from ..VelbusMessage.ModuleInfo.ModuleInfo import ModuleInfo


class NestedAddressVelbusModule(VelbusModule):
    def __init__(self,
                 bus: VelbusProtocol,
                 address: int,
                 module_info: ModuleInfo,
                 update_state_cb: Callable = lambda op, path, value: None):
        super().__init__(bus=bus,
                         address=address,
                         module_info=module_info,
                         update_state_cb=update_state_cb)

        if not hasattr(self, 'addresses'):
            # List of allowed (sub)addresses
            # Wrapped in hasattr to catch the mistake of calling super() after setting self.addresses
            self.addresses = []

    def parse_address(self, address: str) -> Any:
        """
        Parse and validate the address field.
        The default implementation converts the string to int and checks if
        it exists in self.addresses.

        :param address: string of the requested address
        :return: any object representing the address
        :raises: ValueError when the address is invalid
        """
        address = int(address)
        if address not in self.addresses:
            raise ValueError
        return address

    def dispatch(self, path_info: str, request: sanic.request, bus: VelbusProtocol):
        """
        HTTP calls are passed to this method.

        This implementation uses the first component of the path as a (sub)address.
        The second component is handled as in VelbusModule.dispatch:
        as a method name, followed by an underscore, followed by the HTTP
        method (in ALL CAPS).

        e.g. GET /module/01/1/test/foobar
        will call
             module_at_address_01.test_GET(
                subaddress=1,
                path_info='/foobar',
                request=request,
                bus=bus)
        """
        if path_info == '':
            path_info = '/'

        if path_info == '/':
            # generate index
            return sanic.response.text('\r\n'.join([str(_) for _ in self.addresses]) + '\r\n')

        module_path = path_info[1:].split('/', 2)  # skip leading /

        subaddress = module_path.pop(0)
        try:
            subaddress = self.parse_address(subaddress)
        except ValueError:
            return sanic.response.text('subaddress `{}` not found'.format(subaddress), status=404)

        if len(module_path) < 1:
            module_path.append('')

        if len(module_path) < 2:
            module_path.append('')
        else:
            module_path[1] = '/' + module_path[1]

        try:
            return self.lookup_method(module_path[0], request.method)(
                subaddress=subaddress,
                path_info=module_path[1],
                request=request,
                bus=bus,
            )
        except AttributeError:
            return sanic.response.text('{m} for {t} not found\r\n'.format(
                    m=module_path[0],
                    t=self.__class__.__name__,
                ),
                status=404
            )
