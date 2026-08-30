import factory
from django.contrib.auth import get_user_model

StaffUser = get_user_model()


class StaffUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StaffUser
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    role = StaffUser.Role.STAFF
    is_active = True

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw = extracted or "correct-password"
        self.set_password(raw)
        if create:
            self.save(update_fields=["password"])
