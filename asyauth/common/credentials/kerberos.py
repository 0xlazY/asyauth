from typing import List
from asyauth.common.credentials import UniCredential
from asyauth.common.constants import asyauthSecret, asyauthProtocol, asyauthSubProtocol
from asyauth.common.subprotocols import SubProtocol
from asyauth.common.subprotocols import SubProtocolNative
from asysocks.unicomm.common.target import UniTarget
from minikerberos.common.creds import KerberosCredential as KCRED
from minikerberos.pkinit import PKINIT
from asyauth.utils.paramprocessor import str_one, int_one, bool_one, int_list


class KerberosCredential(UniCredential):
	def __init__(self, secret, username, domain, stype:asyauthSecret, target:UniTarget = None, altname:str = None, altdomain:str = None, etypes:List[int] = [23,17,18], subprotocol:SubProtocol = SubProtocolNative()):
		UniCredential.__init__(
			self, 
			secret = secret,
			username = username,
			domain = domain,
			stype = stype,			
			protocol = asyauthProtocol.KERBEROS,
			subprotocol = subprotocol)
		
		self.etypes = etypes
		self.altname = altname
		self.altdomain = altdomain
		self.target = target

		self.dh_params = {
				'p' : int('00ffffffffffffffffc90fdaa22168c234c4c6628b80dc1cd129024e088a67cc74020bbea63b139b22514a08798e3404ddef9519b3cd3a431b302b0a6df25f14374fe1356d6d51c245e485b576625e7ec6f44c42e9a637ed6b0bff5cb6f406b7edee386bfb5a899fa5ae9f24117c4b1fe649286651ece65381ffffffffffffffff', 16),
				'g' : 2
			}

	def get_pkinit(self) -> PKINIT:
		if self.stype == asyauthSecret.CERTSTORE:
			return PKINIT.from_windows_certstore(self.settings.pfx12_file, certstore_name = 'MY', cert_serial = None, dh_params = self.dh_params, is_azure = self.is_azure)
		else:
			return PKINIT.from_pfx(self.settings.pfx12_file, self.settings.pfx12_file_pass, dh_params = self.dh_params, is_azure = self.is_azure)

	@staticmethod
	def get_url_params():
		return {
			'altname' : str_one,
			'altdomain' : str_one,
			'etype' : int_list,
			'dc' : str_one,
			'dns' : str_one,
		}

	def to_ccred(self):
		if self.stype == asyauthSecret.KEYTAB:
			return KCRED.from_keytab(self.secret, self.username, self.domain)
		if self.stype == asyauthSecret.KIRBI:
			return KCRED.from_kirbi(self.secret)

		res = KCRED()
		res.username = self.username
		res.domain = self.domain

		if self.stype in [asyauthSecret.PASSWORD, asyauthSecret.PW, asyauthSecret.PASS]:
			res.password = self.secret
		elif self.stype in [asyauthSecret.NT, asyauthSecret.RC4]:
			if len(self.secret) != 32:
				raise Exception('Incorrect RC4/NT key! %s' % self.secret)
			res.nt_hash = self.secret
			res.kerberos_key_rc4 = self.secret
		elif self.stype == asyauthSecret.AES:
			if len(self.secret) == 32:
				res.kerberos_key_aes_128 = self.secret
			elif len(self.secret) == 64:
				res.kerberos_key_aes_256 = self.secret
			else:
				raise Exception('Incorrect AES key! %s' % self.secret)
		elif self.stype == asyauthSecret.DES:
			if len(self.secret) != 16:
				raise Exception('Incorrect DES key! %s' % self.secret)
			res.kerberos_key_des = self.secret
		elif self.stype in [asyauthSecret.DES3, asyauthSecret.TDES]:
			if len(self.secret) != 24:
				raise Exception('Incorrect DES3 key! %s' % self.secret)
			res.kerberos_key_des3 = self.secret
		elif self.stype == asyauthSecret.CCACHE:
			res.ccache = self.secret
		else:
			raise Exception('Missing/unknown stype!')

		return res

	def build_context(self):
		if self.subprotocol.type == asyauthSubProtocol.NATIVE:
			from asyauth.protocols.kerberos.client.native import KerberosClientNative
			return KerberosClientNative(self)

		elif self.subprotocol.type == asyauthSubProtocol.SSPI:
			from asyauth.protocols.kerberos.client.sspi import KerberosClientSSPI
			return KerberosClientSSPI(self)

		elif self.subprotocol.type == asyauthSubProtocol.SSPIPROXY:
			from asyauth.protocols.kerberos.client.sspiproxy import KerberosClientSSPIProxy
			return KerberosClientSSPIProxy(self)

		elif self.subprotocol.type == asyauthSubProtocol.WSNET:
			from asyauth.protocols.kerberos.client.wsnet import KerberosClientWSNET
			return KerberosClientWSNET(self)
		else:
			raise Exception('Unsupported subprotocol "%s"' % self.subprotocol)

