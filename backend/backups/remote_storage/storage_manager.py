"""
Remote Storage Manager - Gestion professionnelle du stockage distant
Support SMB/CIFS avec authentification sécurisée
"""

import os
import logging
import socket
import platform
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class StorageConnectionError(Exception):
    """Exception levée lors d'erreurs de connexion au stockage"""
    pass


class StorageAuthenticationError(Exception):
    """Exception levée lors d'erreurs d'authentification"""
    pass


class StoragePermissionError(Exception):
    """Exception levée lors d'erreurs de permissions"""
    pass


class RemoteStorageManager:
    """
    Gestionnaire centralisé pour stockage distant

    Fonctionnalités:
    - Test de connectivité réseau (ping, DNS, port)
    - Vérification permissions d'écriture
    - Calcul espace disponible
    - Montage automatique SMB/NFS
    - Gestion des credentials
    """

    def __init__(self, storage_config):
        """
        Initialise le gestionnaire de stockage

        Args:
            storage_config: Instance de RemoteStorageConfig
        """
        self.config = storage_config
        self.protocol = storage_config.protocol
        self.host = storage_config.host
        self.port = storage_config.port
        self.share_name = storage_config.share_name
        self.base_path = storage_config.base_path
        self.username = storage_config.username
        self.domain = storage_config.domain

        self.is_connected = False
        self.connection_error = None
        self._mount_point = None

    def get_base_path(self) -> str:
        """
        Retourne le chemin de base du stockage

        Returns:
            str: Chemin complet vers le stockage
        """
        return self.config.get_full_path()

    def test_connectivity(self, timeout: int = 5) -> Dict[str, Any]:
        """
        Teste la connectivité réseau vers le stockage distant

        Tests effectués:
        1. Résolution DNS
        2. Ping / Test socket TCP
        3. Test port spécifique (445 pour SMB, 2049 pour NFS)

        Args:
            timeout: Timeout en secondes pour chaque test

        Returns:
            Dict contenant les résultats des tests
        """
        results = {
            'dns_resolution': False,
            'tcp_reachable': False,
            'port_open': False,
            'overall_success': False,
            'errors': []
        }

        # 1. Test résolution DNS
        logger.info(f"[STORAGE] Test DNS pour {self.host}...")
        try:
            socket.gethostbyname(self.host)
            results['dns_resolution'] = True
            logger.info(f"[STORAGE] ✓ DNS résolu pour {self.host}")
        except socket.gaierror as e:
            error_msg = f"Impossible de résoudre le nom d'hôte '{self.host}': {e}"
            results['errors'].append(error_msg)
            logger.error(f"[STORAGE] ✗ {error_msg}")
            return results  # Pas de sens de continuer si DNS échoue

        # 2. Test accessibilité TCP
        logger.info(f"[STORAGE] Test accessibilité TCP {self.host}:{self.port}...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.host, self.port))
            sock.close()

            if result == 0:
                results['tcp_reachable'] = True
                results['port_open'] = True
                logger.info(f"[STORAGE] ✓ Port {self.port} ouvert sur {self.host}")
            else:
                error_msg = f"Port {self.port} fermé ou filtré sur {self.host}"
                results['errors'].append(error_msg)
                logger.warning(f"[STORAGE] ✗ {error_msg}")
        except socket.timeout:
            error_msg = f"Timeout lors de la connexion à {self.host}:{self.port}"
            results['errors'].append(error_msg)
            logger.error(f"[STORAGE] ✗ {error_msg}")
        except Exception as e:
            error_msg = f"Erreur lors du test de connexion: {e}"
            results['errors'].append(error_msg)
            logger.error(f"[STORAGE] ✗ {error_msg}")

        # Résultat global
        results['overall_success'] = all([
            results['dns_resolution'],
            results['tcp_reachable'],
            results['port_open']
        ])

        return results

    def test_authentication(self) -> bool:
        """
        Teste l'authentification sur le stockage distant

        Returns:
            bool: True si authentification réussie

        Raises:
            StorageAuthenticationError: Si l'authentification échoue
        """
        logger.info(f"[STORAGE] Test authentification sur {self.config.get_connection_string()}...")

        if self.protocol == 'smb':
            return self._test_smb_authentication()
        elif self.protocol == 'nfs':
            return self._test_nfs_authentication()
        elif self.protocol == 'local':
            return True  # Pas d'auth pour local

        return False

    def _test_smb_authentication(self) -> bool:
        """
        Teste l'authentification SMB

        Pour Windows: Utilise net use
        Pour Linux: Teste smbclient

        Returns:
            bool: True si authentification réussie
        """
        if platform.system() == 'Windows':
            return self._test_smb_windows()
        else:
            return self._test_smb_linux()

    def _test_smb_windows(self) -> bool:
        """
        Teste SMB sous Windows avec net use

        Returns:
            bool: True si le partage est accessible
        """
        import subprocess

        unc_path = f"\\\\{self.host}\\{self.share_name}"

        try:
            # Vérifier si déjà connecté
            result = subprocess.run(
                ['net', 'use'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if unc_path in result.stdout:
                logger.info(f"[STORAGE] ✓ Partage {unc_path} déjà connecté")
                return True

            # Tenter la connexion
            password = self.config.get_password()

            cmd = ['net', 'use', unc_path]
            if self.username:
                user_arg = f"{self.domain}\\{self.username}" if self.domain else self.username
                cmd.extend([f'/user:{user_arg}', password])

            logger.info(f"[STORAGE] Tentative de connexion à {unc_path}...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"[STORAGE] ✓ Connexion SMB réussie à {unc_path}")
                return True
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"[STORAGE] ✗ Échec connexion SMB: {error_msg}")
                raise StorageAuthenticationError(f"Échec authentification SMB: {error_msg}")

        except subprocess.TimeoutExpired:
            logger.error("[STORAGE] ✗ Timeout lors de la connexion SMB")
            raise StorageAuthenticationError("Timeout lors de la connexion SMB")
        except Exception as e:
            logger.error(f"[STORAGE] ✗ Erreur authentification SMB: {e}")
            raise StorageAuthenticationError(f"Erreur authentification SMB: {e}")

    def _test_smb_linux(self) -> bool:
        """
        Teste SMB sous Linux avec smbclient

        Returns:
            bool: True si le partage est accessible
        """
        import subprocess

        try:
            password = self.config.get_password()

            # Construire la commande smbclient
            cmd = [
                'smbclient',
                f'//{self.host}/{self.share_name}',
                '-U', f"{self.domain}\\{self.username}" if self.domain else self.username,
                password,
                '-c', 'ls'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"[STORAGE] ✓ Connexion SMB réussie")
                return True
            else:
                error_msg = result.stderr.strip()
                logger.error(f"[STORAGE] ✗ Échec connexion SMB: {error_msg}")
                raise StorageAuthenticationError(f"Échec authentification SMB: {error_msg}")

        except FileNotFoundError:
            error_msg = "smbclient n'est pas installé. Installez samba-client."
            logger.error(f"[STORAGE] ✗ {error_msg}")
            raise StorageAuthenticationError(error_msg)
        except Exception as e:
            logger.error(f"[STORAGE] ✗ Erreur authentification SMB: {e}")
            raise StorageAuthenticationError(f"Erreur: {e}")

    def _test_nfs_authentication(self) -> bool:
        """
        Pour NFS, pas d'authentification au sens traditionnel
        Vérifie simplement que le point de montage est accessible

        Returns:
            bool: True si accessible
        """
        mount_point = self.get_base_path()

        if not os.path.exists(mount_point):
            logger.warning(f"[STORAGE] Point de montage NFS n'existe pas: {mount_point}")
            return False

        if not os.path.ismount(mount_point):
            logger.warning(f"[STORAGE] {mount_point} n'est pas un point de montage NFS")
            return False

        logger.info(f"[STORAGE] ✓ Point de montage NFS accessible: {mount_point}")
        return True

    def test_write_permissions(self) -> bool:
        """
        Teste les permissions d'écriture sur le stockage

        Returns:
            bool: True si écriture autorisée

        Raises:
            StoragePermissionError: Si permissions insuffisantes
        """
        base_path = self.get_base_path()
        test_file = os.path.join(base_path, '.write_test_esxi_backup')

        logger.info(f"[STORAGE] Test permissions d'écriture sur {base_path}...")

        try:
            # Créer les dossiers si nécessaire
            os.makedirs(base_path, exist_ok=True)

            # Tenter d'écrire un fichier test
            with open(test_file, 'w') as f:
                f.write('test write permission')

            # Vérifier qu'il a bien été créé
            if not os.path.exists(test_file):
                raise StoragePermissionError("Fichier test non créé")

            # Lire le fichier
            with open(test_file, 'r') as f:
                content = f.read()
                if content != 'test write permission':
                    raise StoragePermissionError("Contenu fichier test incorrect")

            # Supprimer le fichier test
            os.remove(test_file)

            logger.info(f"[STORAGE] ✓ Permissions d'écriture validées")
            return True

        except PermissionError as e:
            error_msg = f"Permissions insuffisantes sur {base_path}: {e}"
            logger.error(f"[STORAGE] ✗ {error_msg}")
            raise StoragePermissionError(error_msg)
        except Exception as e:
            error_msg = f"Erreur lors du test d'écriture: {e}"
            logger.error(f"[STORAGE] ✗ {error_msg}")
            raise StoragePermissionError(error_msg)

    def get_available_space(self) -> int:
        """
        Calcule l'espace disponible sur le stockage

        Returns:
            int: Espace disponible en bytes
        """
        base_path = self.get_base_path()

        try:
            if platform.system() == 'Windows':
                import ctypes

                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(base_path),
                    None,
                    None,
                    ctypes.pointer(free_bytes)
                )
                available_bytes = free_bytes.value
            else:
                # Unix/Linux
                stat = os.statvfs(base_path)
                available_bytes = stat.f_bavail * stat.f_frsize

            available_gb = available_bytes / (1024 ** 3)
            logger.info(f"[STORAGE] Espace disponible: {available_gb:.2f} GB")

            return available_bytes

        except Exception as e:
            logger.error(f"[STORAGE] Erreur calcul espace disponible: {e}")
            return 0

    def connect(self) -> bool:
        """
        Établit la connexion au stockage distant

        Effectue tous les tests nécessaires:
        1. Connectivité réseau
        2. Authentification
        3. Permissions d'écriture

        Returns:
            bool: True si connexion réussie

        Raises:
            StorageConnectionError: Si la connexion échoue
        """
        logger.info(f"[STORAGE] === CONNEXION AU STOCKAGE DISTANT ===")
        logger.info(f"[STORAGE] Configuration: {self.config.name}")
        logger.info(f"[STORAGE] Protocole: {self.protocol}")
        logger.info(f"[STORAGE] Chemin: {self.get_base_path()}")

        try:
            # 1. Test connectivité
            connectivity = self.test_connectivity()
            if not connectivity['overall_success']:
                errors = ', '.join(connectivity['errors'])
                raise StorageConnectionError(f"Échec tests connectivité: {errors}")

            # 2. Test authentification
            if self.protocol in ['smb', 'nfs']:
                auth_success = self.test_authentication()
                if not auth_success:
                    raise StorageAuthenticationError("Échec authentification")

            # 3. Test permissions
            self.test_write_permissions()

            # 4. Vérifier espace disponible
            available_space = self.get_available_space()
            if available_space < 1024 * 1024 * 1024:  # 1 GB minimum
                logger.warning(f"[STORAGE] ⚠ Espace disponible faible: {available_space / (1024**3):.2f} GB")

            self.is_connected = True
            logger.info(f"[STORAGE] ✓✓✓ CONNEXION RÉUSSIE ✓✓✓")

            return True

        except Exception as e:
            self.is_connected = False
            self.connection_error = str(e)
            logger.error(f"[STORAGE] ✗✗✗ ÉCHEC CONNEXION: {e} ✗✗✗")
            raise

    def disconnect(self):
        """
        Déconnexion du stockage distant (si nécessaire)
        """
        if self.protocol == 'smb' and platform.system() == 'Windows':
            try:
                import subprocess
                unc_path = f"\\\\{self.host}\\{self.share_name}"
                subprocess.run(
                    ['net', 'use', unc_path, '/delete'],
                    capture_output=True,
                    timeout=10
                )
                logger.info(f"[STORAGE] Déconnexion de {unc_path}")
            except Exception as e:
                logger.warning(f"[STORAGE] Erreur lors de la déconnexion: {e}")

        self.is_connected = False

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False
