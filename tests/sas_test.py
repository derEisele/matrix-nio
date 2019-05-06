import pytest

from datetime import timedelta
from nio.crypto import Sas, SasState, OlmDevice
from nio.exceptions import LocalProtocolError
from nio.events import (
    KeyVerificationStart,
    KeyVerificationAccept,
    KeyVerificationKey,
    KeyVerificationMac,
    KeyVerificationCancel
)
from helpers import faker

alice_id = "@alice:example.org"
alice_device_id = "JLAFKJWSCS"
alice_keys = faker.olm_key_pair()

bob_id = "@bob:example.org"
bob_device_id = "JLAFKJWSRS"
bob_keys = faker.olm_key_pair()

alice_device = OlmDevice(
    alice_id,
    alice_device_id,
    alice_keys["ed25519"],
    alice_keys["curve25519"]
)

bob_device = OlmDevice(
    bob_id,
    bob_device_id,
    bob_keys["ed25519"],
    bob_keys["curve25519"]
)


class TestClass(object):
    def test_sas_creation(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device
        )

        with pytest.raises(LocalProtocolError):
            alice.accept_verification()

    def test_sas_start(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )
        assert alice.state == SasState.created

        start = {
            "sender": alice_id,
            "content": alice.start_verification().content
        }

        start_event = KeyVerificationStart.from_dict(start)
        assert isinstance(start_event, KeyVerificationStart)

        bob = Sas.from_key_verification_start(
            bob_id,
            bob_device_id,
            bob_keys["ed25519"],
            alice_device,
            start_event
        )

        with pytest.raises(LocalProtocolError):
            bob.start_verification()

        assert bob.state == SasState.started

    def test_sas_accept(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )
        start = {
            "sender": alice_id,
            "content": alice.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)

        bob = Sas.from_key_verification_start(
            bob_id,
            bob_device,
            bob_keys["ed25519"],
            alice_device,
            start_event
        )

        accept = {
            "sender": bob_id,
            "content": bob.accept_verification().content
        }
        accept_event = KeyVerificationAccept.from_dict(accept)
        assert isinstance(accept_event, KeyVerificationAccept)
        alice.receive_accept_event(accept_event)
        assert alice.state == SasState.accepted

    def test_sas_share_keys(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )
        start = {
            "sender": alice_id,
            "content": alice.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)

        bob = Sas.from_key_verification_start(
            bob_id,
            bob_device_id,
            bob_keys["ed25519"],
            alice_device,
            start_event
        )

        accept = {
            "sender": bob_id,
            "content": bob.accept_verification().content
        }
        accept_event = KeyVerificationAccept.from_dict(accept)
        alice.receive_accept_event(accept_event)

        alice_key = {
            "sender": alice_id,
            "content": alice.share_key().content
        }

        key_event = KeyVerificationKey.from_dict(alice_key)
        assert isinstance(key_event, KeyVerificationKey)
        bob.receive_key_event(key_event)
        assert bob.state == SasState.key_received

        bob_key = {
            "sender": bob_id,
            "content": bob.share_key().content
        }

        key_event = KeyVerificationKey.from_dict(bob_key)
        assert isinstance(key_event, KeyVerificationKey)
        alice.receive_key_event(key_event)
        assert alice.state == SasState.key_received
        assert alice.get_emoji() == bob.get_emoji()

    def test_sas_decimals(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )
        start = {
            "sender": alice_id,
            "content": alice.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)

        bob = Sas.from_key_verification_start(
            bob_id,
            bob_device_id,
            bob_keys["ed25519"],
            alice_device,
            start_event
        )

        alice.set_their_pubkey(bob.pubkey)
        bob.set_their_pubkey(alice.pubkey)

        assert alice.get_decimals() == bob.get_decimals()

    def test_sas_invalid_commitment(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )
        start = {
            "sender": alice_id,
            "content": alice.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)

        bob = Sas.from_key_verification_start(
            bob_id,
            bob_device_id,
            bob_keys["ed25519"],
            alice_device,
            start_event
        )

        accept = {
            "sender": bob_id,
            "content": bob.accept_verification().content
        }
        accept_event = KeyVerificationAccept.from_dict(accept)
        alice.receive_accept_event(accept_event)

        alice_key = {
            "sender": alice_id,
            "content": alice.share_key().content
        }

        key_event = KeyVerificationKey.from_dict(alice_key)
        assert isinstance(key_event, KeyVerificationKey)
        bob.receive_key_event(key_event)
        assert bob.state == SasState.key_received

        bob_key = {
            "sender": bob_id,
            "content": bob.share_key().content
        }

        bob_key["content"]["key"] = alice.pubkey
        key_event = KeyVerificationKey.from_dict(bob_key)
        assert isinstance(key_event, KeyVerificationKey)
        alice.receive_key_event(key_event)
        assert alice.state == SasState.canceled

    def test_sas_mac(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )
        start = {
            "sender": alice_id,
            "content": alice.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)

        bob = Sas.from_key_verification_start(
            bob_id,
            bob_device_id,
            bob_keys["ed25519"],
            alice_device,
            start_event
        )

        with pytest.raises(LocalProtocolError):
            alice.accept_sas()

        alice.set_their_pubkey(bob.pubkey)
        bob.set_their_pubkey(alice.pubkey)

        alice.state = SasState.key_received
        bob.state = SasState.key_received
        alice.chosen_mac_method = Sas._mac_normal
        bob.chosen_mac_method = Sas._mac_normal

        with pytest.raises(LocalProtocolError):
            alice.get_mac()

        alice.accept_sas()
        alice_mac = {
            "sender": alice_id,
            "content": alice.get_mac().content
        }

        mac_event = KeyVerificationMac.from_dict(alice_mac)
        assert isinstance(mac_event, KeyVerificationMac)
        assert not bob.verified

        bob.receive_mac_event(mac_event)
        assert bob.state == SasState.mac_received
        assert not bob.verified

        bob.accept_sas()
        assert bob.verified

    def test_sas_cancelation(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )
        assert not alice.canceled

        with pytest.raises(LocalProtocolError):
            alice.get_cancelation()

        alice.cancel()
        assert alice.canceled

        with pytest.raises(LocalProtocolError):
            alice.start_verification()

        cancelation = alice.get_cancelation().content
        assert cancelation == {
            "transaction_id": alice.transaction_id,
            "code": "m.user",
            "reason": "Canceled by user"
        }

    def test_sas_invalid_start(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )

        start = {
            "sender": alice_id,
            "content": alice.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)
        start_event.method = "m.sas.v0"

        bob = Sas.from_key_verification_start(
            bob_id,
            bob_device_id,
            bob_keys["ed25519"],
            alice_device,
            start_event
        )

        assert bob.canceled

    def test_sas_reject(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )

        start = {
            "sender": alice_id,
            "content": alice.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)

        bob = Sas.from_key_verification_start(
            bob_id,
            bob_device_id,
            bob_keys["ed25519"],
            alice_device,
            start_event
        )

        with pytest.raises(LocalProtocolError):
            alice.reject_sas()

        alice.set_their_pubkey(bob.pubkey)
        bob.set_their_pubkey(alice.pubkey)
        alice.state = SasState.key_received
        bob.state = SasState.key_received

        alice.reject_sas()

        assert alice.canceled

    def test_sas_timeout(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )

        assert not alice.timed_out

        minute = timedelta(minutes=1)
        alice.creation_time -= minute

        assert not alice.timed_out
        alice.creation_time -= (minute * 4)
        assert alice.timed_out
        assert alice.canceled

    def test_sas_event_timeout(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )
        minute = timedelta(minutes=1)

        assert not alice.timed_out
        alice._last_event_time -= minute
        assert alice.timed_out
        assert alice.canceled

    def test_sas_invalid_mac(self):
        alice = Sas(
            alice_id,
            alice_device_id,
            alice_keys["ed25519"],
            bob_device,
        )
        start = {
            "sender": alice_id,
            "content": alice.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)

        bob = Sas.from_key_verification_start(
            bob_id,
            bob_device_id,
            bob_keys["ed25519"],
            alice_device,
            start_event
        )

        with pytest.raises(LocalProtocolError):
            alice.accept_sas()

        alice.set_their_pubkey(bob.pubkey)
        bob.set_their_pubkey(alice.pubkey)

        alice.state = SasState.key_received
        bob.state = SasState.key_received
        alice.chosen_mac_method = Sas._mac_normal
        bob.chosen_mac_method = Sas._mac_normal

        alice.accept_sas()
        alice_mac = {
            "sender": alice_id,
            "content": alice.get_mac().content
        }

        mac_event = KeyVerificationMac.from_dict(alice_mac)
        mac_event.keys = "FAKEKEYS"

        bob.receive_mac_event(mac_event)
        assert bob.canceled
        assert not bob.verified

        bob.state = SasState.key_received
        assert not bob.canceled

        mac_event = KeyVerificationMac.from_dict(alice_mac)
        mac_event.mac["ed25519:{}".format(alice_device_id)] = "FAKEKEYS"

        bob.receive_mac_event(mac_event)
        assert bob.canceled
        assert not bob.verified

    def test_client_creation(self, olm_machine):
        bob_sas = Sas(
            bob_id,
            bob_device_id,
            olm_machine.account.identity_keys["ed25519"],
            bob_device
        )

        start = {
            "sender": bob_id,
            "content": bob_sas.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)

        assert olm_machine.device_store[bob_id][bob_device_id]
        olm_machine.handle_key_verification(start_event)

        alice_sas = olm_machine.key_verifications[start_event.transaction_id]

        assert alice_sas

    def test_client_gc(self, olm_machine):
        bob_sas = Sas(
            bob_id,
            bob_device_id,
            olm_machine.account.identity_keys["ed25519"],
            bob_device
        )

        start = {
            "sender": bob_id,
            "content": bob_sas.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)
        olm_machine.handle_key_verification(start_event)
        alice_sas = olm_machine.key_verifications[start_event.transaction_id]
        alice_sas.cancel()
        olm_machine.clear_verifications()
        alice_sas = olm_machine.key_verifications[start_event.transaction_id]
        assert alice_sas
        alice_sas.creation_time -= timedelta(minutes=25)
        olm_machine.clear_verifications()
        with pytest.raises(KeyError):
            alice_sas = (
                olm_machine.key_verifications[start_event.transaction_id]
            )

    def test_client_full_sas(self, olm_machine):
        alice_device = OlmDevice(
            olm_machine.user_id,
            olm_machine.device_id,
            olm_machine.account.identity_keys["ed25519"],
            olm_machine.account.identity_keys["curve25519"],
        )
        bob_device = olm_machine.device_store[bob_id][bob_device_id]
        bob_sas = Sas(
            bob_id,
            bob_device_id,
            bob_device.ed25519,
            alice_device,
        )

        start = {
            "sender": bob_id,
            "content": bob_sas.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)

        assert olm_machine.device_store[bob_id][bob_device_id]
        olm_machine.handle_key_verification(start_event)

        alice_sas = olm_machine.key_verifications[start_event.transaction_id]

        accept = {
            "sender": olm_machine.user_id,
            "content": alice_sas.accept_verification().content
        }
        accept_event = KeyVerificationAccept.from_dict(accept)

        bob_sas.receive_accept_event(accept_event)

        bob_key = {
            "sender": bob_id,
            "content": bob_sas.share_key().content
        }
        bob_key_event = KeyVerificationKey.from_dict(bob_key)

        olm_machine.handle_key_verification(bob_key_event)

        alice_key = {
            "sender": alice_id,
            "content": alice_sas.share_key().content
        }
        alice_key_event = KeyVerificationKey.from_dict(alice_key)
        bob_sas.receive_key_event(alice_key_event)

        assert alice_sas.other_key_set
        assert bob_sas.other_key_set

        bob_sas.accept_sas()

        bob_mac = {
            "sender": bob_id,
            "content": bob_sas.get_mac().content
        }

        bob_mac_event = KeyVerificationMac.from_dict(bob_mac)

        olm_machine.handle_key_verification(bob_mac_event)
        assert alice_sas.state == SasState.mac_received
        assert not alice_sas.verified

        alice_sas.accept_sas()
        assert alice_sas.verified

    def test_client_invalid_key(self, olm_machine):
        alice_device = OlmDevice(
            olm_machine.user_id,
            olm_machine.device_id,
            olm_machine.account.identity_keys["ed25519"],
            olm_machine.account.identity_keys["curve25519"],
        )
        bob_sas = Sas(
            bob_id,
            bob_device_id,
            faker.olm_key_pair()["ed25519"],
            alice_device,
        )

        start = {
            "sender": bob_id,
            "content": bob_sas.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)

        assert olm_machine.device_store[bob_id][bob_device_id]
        olm_machine.handle_key_verification(start_event)

        alice_sas = olm_machine.key_verifications[start_event.transaction_id]

        accept = {
            "sender": olm_machine.user_id,
            "content": alice_sas.accept_verification().content
        }
        accept_event = KeyVerificationAccept.from_dict(accept)

        bob_sas.receive_accept_event(accept_event)

        bob_key = {
            "sender": bob_id,
            "content": bob_sas.share_key().content
        }
        bob_key_event = KeyVerificationKey.from_dict(bob_key)

        olm_machine.handle_key_verification(bob_key_event)

        alice_key = {
            "sender": alice_id,
            "content": alice_sas.share_key().content
        }
        alice_key_event = KeyVerificationKey.from_dict(alice_key)
        bob_sas.receive_key_event(alice_key_event)

        assert alice_sas.other_key_set
        assert bob_sas.other_key_set

        bob_sas.accept_sas()

        bob_mac = {
            "sender": bob_id,
            "content": bob_sas.get_mac().content
        }

        bob_mac_event = KeyVerificationMac.from_dict(bob_mac)

        olm_machine.handle_key_verification(bob_mac_event)
        assert alice_sas.state == SasState.canceled
        assert not alice_sas.verified

        with pytest.raises(LocalProtocolError):
            alice_sas.accept_sas()

    def test_client_full_we_start(self, olm_machine):
        alice_device = OlmDevice(
            olm_machine.user_id,
            olm_machine.device_id,
            olm_machine.account.identity_keys["ed25519"],
            olm_machine.account.identity_keys["curve25519"],
        )
        bob_device = olm_machine.device_store[bob_id][bob_device_id]

        start = {
            "sender": alice_device.user_id,
            "content": olm_machine.create_sas(bob_device).content
        }
        start_event = KeyVerificationStart.from_dict(start)

        bob_sas = Sas.from_key_verification_start(
            bob_device.user_id,
            bob_device.id,
            bob_device.ed25519,
            alice_device,
            start_event
        )

        alice_sas = olm_machine.key_verifications[start_event.transaction_id]
        assert alice_sas

        accept = {
            "sender": bob_id,
            "content": bob_sas.accept_verification().content
        }
        accept_event = KeyVerificationAccept.from_dict(accept)
        olm_machine.handle_key_verification(accept_event)

        alice_key = {
            "sender": alice_id,
            "content": alice_sas.share_key().content
        }
        alice_key_event = KeyVerificationKey.from_dict(alice_key)
        bob_sas.receive_key_event(alice_key_event)

        bob_key = {
            "sender": bob_id,
            "content": bob_sas.share_key().content
        }
        bob_key_event = KeyVerificationKey.from_dict(bob_key)

        olm_machine.handle_key_verification(bob_key_event)

        assert alice_sas.other_key_set
        assert bob_sas.other_key_set

        bob_sas.accept_sas()

        bob_mac = {
            "sender": bob_id,
            "content": bob_sas.get_mac().content
        }

        bob_mac_event = KeyVerificationMac.from_dict(bob_mac)

        assert not olm_machine.is_device_verified(bob_device)
        alice_sas.accept_sas()
        olm_machine.handle_key_verification(bob_mac_event)
        assert alice_sas.state == SasState.mac_received
        assert alice_sas.verified
        assert olm_machine.is_device_verified(bob_device)

    def test_client_unknown_device(self, olm_machine):
        alice_device = OlmDevice(
            olm_machine.user_id,
            olm_machine.device_id,
            olm_machine.account.identity_keys["ed25519"],
            olm_machine.account.identity_keys["curve25519"],
        )

        bob_device = faker.olm_device()

        bob_sas = Sas(
            bob_device.user_id,
            bob_device.id,
            bob_device.ed25519,
            alice_device
        )

        start = {
            "sender": bob_device.user_id,
            "content": bob_sas.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)
        olm_machine.handle_key_verification(start_event)

        assert start_event.transaction_id not in olm_machine.key_verifications
        assert bob_device.user_id in olm_machine.users_for_key_query

    def test_client_unsupported_method(self, olm_machine):
        alice_device = OlmDevice(
            olm_machine.user_id,
            olm_machine.device_id,
            olm_machine.account.identity_keys["ed25519"],
            olm_machine.account.identity_keys["curve25519"],
        )
        bob_device = olm_machine.device_store[bob_id][bob_device_id]

        bob_sas = Sas(
            bob_device.user_id,
            bob_device.id,
            bob_device.ed25519,
            alice_device
        )

        start = {
            "sender": bob_device.user_id,
            "content": bob_sas.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)
        start_event.method = "unsupported"
        assert not olm_machine.outgoing_to_device_messages

        olm_machine.handle_key_verification(start_event)

        assert start_event.transaction_id not in olm_machine.key_verifications
        assert olm_machine.outgoing_to_device_messages
        to_device = olm_machine.outgoing_to_device_messages[0]
        assert (
            start_event.transaction_id == to_device.content["transaction_id"]
        )

    def test_client_unknown_txid(self, olm_machine):
        alice_device = OlmDevice(
            olm_machine.user_id,
            olm_machine.device_id,
            olm_machine.account.identity_keys["ed25519"],
            olm_machine.account.identity_keys["curve25519"],
        )
        bob_device = olm_machine.device_store[bob_id][bob_device_id]

        bob_sas = Sas(
            bob_device.user_id,
            bob_device.id,
            bob_device.ed25519,
            alice_device
        )

        start = {
            "sender": bob_device.user_id,
            "content": bob_sas.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)
        olm_machine.handle_key_verification(start_event)

        bob_key = {
            "sender": bob_id,
            "content": bob_sas.share_key().content
        }
        bob_key_event = KeyVerificationKey.from_dict(bob_key)
        bob_key_event.transaction_id = "unknown"
        olm_machine.handle_key_verification(bob_key_event)
        alice_sas = olm_machine.key_verifications[start_event.transaction_id]
        assert alice_sas
        assert not alice_sas.other_key_set

        assert (
            bob_key_event.transaction_id not in olm_machine.key_verifications
        )

    def test_client_accept_cancel(self, olm_machine):
        alice_device = OlmDevice(
            olm_machine.user_id,
            olm_machine.device_id,
            olm_machine.account.identity_keys["ed25519"],
            olm_machine.account.identity_keys["curve25519"],
        )
        bob_device = olm_machine.device_store[bob_id][bob_device_id]

        start = {
            "sender": alice_device.user_id,
            "content": olm_machine.create_sas(bob_device).content
        }
        start_event = KeyVerificationStart.from_dict(start)

        bob_sas = Sas.from_key_verification_start(
            bob_device.user_id,
            bob_device.id,
            bob_device.ed25519,
            alice_device,
            start_event
        )

        alice_sas = olm_machine.key_verifications[start_event.transaction_id]
        assert alice_sas

        accept = {
            "sender": bob_id,
            "content": bob_sas.accept_verification().content
        }
        accept_event = KeyVerificationAccept.from_dict(accept)
        olm_machine.handle_key_verification(accept_event)
        assert not alice_sas.canceled
        olm_machine.handle_key_verification(accept_event)
        assert alice_sas.canceled

    def test_client_cancel_event(self, olm_machine):
        alice_device = OlmDevice(
            olm_machine.user_id,
            olm_machine.device_id,
            olm_machine.account.identity_keys["ed25519"],
            olm_machine.account.identity_keys["curve25519"],
        )
        bob_device = olm_machine.device_store[bob_id][bob_device_id]

        start = {
            "sender": alice_device.user_id,
            "content": olm_machine.create_sas(bob_device).content
        }
        start_event = KeyVerificationStart.from_dict(start)

        bob_sas = Sas.from_key_verification_start(
            bob_device.user_id,
            bob_device.id,
            bob_device.ed25519,
            alice_device,
            start_event
        )

        alice_sas = olm_machine.key_verifications[start_event.transaction_id]
        assert alice_sas

        bob_sas.cancel()
        cancel = {
            "sender": bob_id,
            "content": bob_sas.get_cancelation().content
        }
        cancel_event = KeyVerificationCancel.from_dict(cancel)
        assert not alice_sas.canceled
        olm_machine.handle_key_verification(cancel_event)
        assert alice_sas.canceled
        assert alice_sas.transaction_id not in olm_machine.key_verifications

    def test_key_cancel(self, olm_machine):
        alice_device = OlmDevice(
            olm_machine.user_id,
            olm_machine.device_id,
            olm_machine.account.identity_keys["ed25519"],
            olm_machine.account.identity_keys["curve25519"],
        )
        bob_device = olm_machine.device_store[bob_id][bob_device_id]

        bob_sas = Sas(
            bob_device.user_id,
            bob_device.id,
            bob_device.ed25519,
            alice_device
        )

        start = {
            "sender": bob_device.user_id,
            "content": bob_sas.start_verification().content
        }
        start_event = KeyVerificationStart.from_dict(start)
        olm_machine.handle_key_verification(start_event)

        bob_key = {
            "sender": bob_id,
            "content": bob_sas.share_key().content
        }
        assert not olm_machine.outgoing_to_device_messages
        bob_key_event = KeyVerificationKey.from_dict(bob_key)
        olm_machine.handle_key_verification(bob_key_event)
        alice_sas = olm_machine.key_verifications[start_event.transaction_id]

        assert alice_sas
        assert not alice_sas.canceled
        assert alice_sas.other_key_set

        olm_machine.handle_key_verification(bob_key_event)
        assert alice_sas.canceled
        assert olm_machine.outgoing_to_device_messages
        to_device = olm_machine.outgoing_to_device_messages[0]
        assert (
            start_event.transaction_id == to_device.content["transaction_id"]
        )
