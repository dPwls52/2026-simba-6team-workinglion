import datetime
import shutil
import tempfile
from io import BytesIO

from PIL import Image
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Profile
from .models import Pot, PotAvatar, Proof, Vote


class CoreFlowTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()

        self.host = User.objects.create_user(username='host@test.com', password='Password1')
        self.member = User.objects.create_user(username='member@test.com', password='Password1')
        self.outsider = User.objects.create_user(username='outsider@test.com', password='Password1')

        Profile.objects.create(user=self.host, nickname='호스트')
        Profile.objects.create(user=self.member, nickname='멤버')
        Profile.objects.create(user=self.outsider, nickname='외부인')

        self.pot = Pot.objects.create(
            host=self.host,
            pot_name='아침 운동',
            days=7,
            fee=700,
            total_prize=2600,
            pot_people=3,
            pot_code='ABC123',
        )
        self.pot.participants.add(self.host, self.member)
        PotAvatar.objects.create(pot=self.pot, user=self.host, color='blue')
        PotAvatar.objects.create(pot=self.pot, user=self.member, color='pink')

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def make_image(self, name='proof.png'):
        image_data = BytesIO()
        Image.new('RGB', (10, 10), color='white').save(image_data, format='PNG')
        return SimpleUploadedFile(name, image_data.getvalue(), content_type='image/png')

    def test_dashboard_requires_login_and_has_d_day(self):
        response = self.client.get(reverse('main:dashboard'))
        self.assertRedirects(response, reverse('accounts:login'))

        self.client.force_login(self.host)
        response = self.client.get(reverse('main:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['pots'][0].d_day, 6)

    def test_create_rejects_missing_values_without_server_error(self):
        self.client.force_login(self.host)
        response = self.client.post(reverse('main:create'), {
            'pot-name': '',
            'challenge_term': '7',
            'people': '2',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '팟 이름을 입력해주세요.')
        self.assertEqual(Pot.objects.count(), 1)

    def test_join_normalizes_entry_code_and_deducts_points(self):
        self.client.force_login(self.outsider)
        response = self.client.post(reverse('main:join_pot_action'), {
            'entry_code': ' abc123 ',
        })
        self.assertRedirects(
            response,
            reverse('main:avatar_setting', args=[self.pot.id]),
        )
        self.assertTrue(self.pot.participants.filter(id=self.outsider.id).exists())
        self.outsider.profile.refresh_from_db()
        self.assertEqual(self.outsider.profile.point, 2800)

    def test_item_rejects_invalid_or_nonparticipant_target(self):
        self.client.force_login(self.host)
        detail_url = reverse('main:pot_detail', args=[self.pot.id])
        original_point = self.host.profile.point

        self.client.post(detail_url, {
            'treat-item': 'invalid-item',
            'select-people': str(self.member.id),
        })
        self.host.profile.refresh_from_db()
        self.assertEqual(self.host.profile.point, original_point)

        self.client.post(detail_url, {
            'treat-item': 'post',
            'select-people': str(self.outsider.id),
        })
        self.host.profile.refresh_from_db()
        self.assertEqual(self.host.profile.point, original_point)

        self.client.post(detail_url, {
            'treat-item': 'post',
            'select-people': 'not-a-number',
        })
        self.host.profile.refresh_from_db()
        self.assertEqual(self.host.profile.point, original_point)

    def test_valid_item_deducts_points_and_updates_avatar(self):
        self.client.force_login(self.host)
        response = self.client.post(reverse('main:pot_detail', args=[self.pot.id]), {
            'treat-item': 'post',
            'select-people': str(self.member.id),
        })
        self.assertRedirects(response, reverse('main:pot_detail', args=[self.pot.id]))

        self.host.profile.refresh_from_db()
        member_avatar = PotAvatar.objects.get(pot=self.pot, user=self.member)
        self.assertEqual(self.host.profile.point, 3450)
        self.assertEqual(member_avatar.item, 'post')
        self.assertIsNotNone(member_avatar.item_applied_at)

    def test_nonparticipant_cannot_access_photo_pages(self):
        self.client.force_login(self.outsider)
        before_url = reverse('main:before_photo', args=[self.pot.id])
        after_url = reverse('main:after_photo', args=[self.pot.id])
        self.assertRedirects(self.client.get(before_url), reverse('main:dashboard'))
        self.assertRedirects(self.client.get(after_url), reverse('main:dashboard'))

    def test_photo_upload_redirects_to_after_photo_and_blocks_duplicate(self):
        self.client.force_login(self.host)
        before_url = reverse('main:before_photo', args=[self.pot.id])
        after_url = reverse('main:after_photo', args=[self.pot.id])

        response = self.client.post(before_url, {'image': self.make_image()})
        self.assertRedirects(response, after_url)
        self.assertEqual(Proof.objects.filter(pot=self.pot, user=self.host).count(), 1)

        response = self.client.post(before_url, {'image': self.make_image('second.png')})
        self.assertRedirects(response, after_url)
        self.assertEqual(Proof.objects.filter(pot=self.pot, user=self.host).count(), 1)

    def test_invalid_proof_is_not_shown_as_authenticated(self):
        self.client.force_login(self.host)
        before_url = reverse('main:before_photo', args=[self.pot.id])
        self.client.post(before_url, {'image': self.make_image()})
        Proof.objects.filter(pot=self.pot, user=self.host).update(is_valid=False)

        response = self.client.get(reverse('main:pot_detail', args=[self.pot.id]))
        host_info = None
        for info in response.context['participant_infos']:
            if info['user'] == self.host:
                host_info = info
        self.assertIsNotNone(host_info)
        self.assertIsNone(host_info['proof'])
    def test_host_pays_fee_and_auth_days_are_saved(self):
        self.client.force_login(self.host)
        response = self.client.post(reverse('main:create'), {
            'pot-name': '저녁 독서',
            'challenge_term': '7',
            'people': '2',
            'auth_mon': 'mon',
            'auth_wed': 'wed',
        })

        new_pot = Pot.objects.get(pot_name='저녁 독서')
        self.assertRedirects(response, reverse('main:avatar_setting', args=[new_pot.id]))
        self.host.profile.refresh_from_db()
        self.assertEqual(self.host.profile.point, 2800)
        self.assertEqual(new_pot.total_prize, 1200)
        self.assertEqual(new_pot.auth_days, 'mon,wed')

    def test_non_auth_day_blocks_photo_upload(self):
        today = datetime.date.today()
        blocked_day = (today.weekday() + 1) % 7
        day_codes = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        self.pot.auth_days = day_codes[blocked_day]
        self.pot.save()

        self.client.force_login(self.host)
        response = self.client.post(
            reverse('main:before_photo', args=[self.pot.id]),
            {'image': self.make_image()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '오늘은 인증 요일이 아닙니다.')
        self.assertFalse(Proof.objects.filter(pot=self.pot, user=self.host).exists())

    def test_item_expires_after_48_hours(self):
        avatar = PotAvatar.objects.get(pot=self.pot, user=self.member)
        avatar.item = 'post'
        avatar.item_applied_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=49)
        avatar.save()

        self.client.force_login(self.host)
        self.client.get(reverse('main:pot_detail', args=[self.pot.id]))

        avatar.refresh_from_db()
        self.assertIsNone(avatar.item)
        self.assertIsNone(avatar.item_applied_at)

    def test_vote_can_invalidate_and_restore_proof(self):
        proof = Proof.objects.create(
            pot=self.pot,
            user=self.member,
            image=self.make_image('vote.png'),
        )
        self.client.force_login(self.host)
        vote_url = reverse('main:photo_vote', args=[self.pot.id, self.member.id])

        response = self.client.post(vote_url, {'vote': 'reject'})
        self.assertRedirects(response, vote_url)
        proof.refresh_from_db()
        self.assertFalse(proof.is_valid)
        self.assertEqual(Vote.objects.filter(proof=proof, voter=self.host).count(), 1)

        self.client.post(vote_url, {'vote': 'approve'})
        proof.refresh_from_db()
        self.assertTrue(proof.is_valid)
        self.assertEqual(Vote.objects.filter(proof=proof, voter=self.host).count(), 1)

    def test_completion_pays_successful_user_once_and_failure_has_no_extra_charge(self):
        today = datetime.date.today()
        self.pot.start_date = today - datetime.timedelta(days=7)
        self.pot.auth_days = 'mon,tue,wed,thu,fri,sat,sun'
        self.pot.save()

        self.host.profile.point = 2800
        self.host.profile.save()
        self.member.profile.point = 2800
        self.member.profile.save()

        for day_number in range(6):
            proof = Proof.objects.create(
                pot=self.pot,
                user=self.member,
                image=self.make_image('complete-' + str(day_number) + '.png'),
            )
            proof_date = self.pot.start_date + datetime.timedelta(days=day_number)
            Proof.objects.filter(pk=proof.pk).update(auth_date=proof_date)

        self.client.force_login(self.host)
        complete_url = reverse('main:complete', args=[self.pot.id])
        response = self.client.get(complete_url)
        self.assertEqual(response.status_code, 200)

        self.host.profile.refresh_from_db()
        self.member.profile.refresh_from_db()
        self.pot.refresh_from_db()
        self.assertEqual(self.host.profile.point, 2800)
        self.assertEqual(self.member.profile.point, 4700)
        self.assertTrue(self.pot.is_completed)

        self.client.get(complete_url)
        self.member.profile.refresh_from_db()
        self.assertEqual(self.member.profile.point, 4700)
