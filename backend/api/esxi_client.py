from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl

def connect_to_esxi(host, user, password):
    context = ssl._create_unverified_context()
    return SmartConnect(host=host, user=user, pwd=password, sslContext=context)

def list_vms(si):
    content = si.RetrieveContent()
    vms = []
    for child in content.rootFolder.childEntity:
        if hasattr(child, 'vmFolder'):
            for vm in child.vmFolder.childEntity:
                vms.append(vm.name)
    return vms
