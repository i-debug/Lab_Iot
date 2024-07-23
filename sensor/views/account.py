from django.shortcuts import render, redirect, HttpResponse
from django import forms
from sensor.utils.encrypt import md5
from sensor.models import Admin
from sensor.utils.code import check_code
from io import BytesIO


class LoginForm(forms.Form):
    # 添加表单字段
    username = forms.CharField(
        label='用户名',
        widget=forms.TextInput,
        required=True,
    )
    password = forms.CharField(
        label='密码',
        widget=forms.PasswordInput(render_value=True),
        required=True,
    )

    # code = forms.CharField(
    #     label="验证码",
    #     widget=forms.TextInput,
    #     required=True,
    # )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['placeholder'] = field.label
            else:
                field.widget.attrs = {'class': 'form-control', 'placeholder': field.label}

    def clean_password(self):
        pwd = self.cleaned_data.get("password")
        return md5(pwd)


def login(request):
    if request.method == 'GET':
        form = LoginForm()
        return render(request, 'login.html', {"form": form})

    form = LoginForm(data=request.POST)
    if form.is_valid():
        # user_input_code = form.cleaned_data.pop('code')
        # code = request.session.get('image_code', "")
        # if code.upper() != user_input_code.upper():
        #     form.add_error("code", "验证码错误")
        #     return render(request, 'login.html', {"form": form})

        # 超级用户admin
        if form.cleaned_data.get('username') == 'admin':
            request.session["info"] = {'id': 1, 'name': 'admin'}
            # session save 7 days
            request.session.set_expiry(60 * 60 * 24 * 7)
            return redirect("/sysinfo/state/")

        admin_object = Admin.objects.filter(**form.cleaned_data).first()
        if not admin_object:
            form.add_error("password", "用户名或密码错误")
            return render(request, 'login.html', {"form": form})

        request.session["info"] = {'id': admin_object.id, 'name': admin_object.username}
        # session save 7days
        request.session.set_expiry(60 * 60 * 24 * 7)
        return redirect("/sysinfo/state/")

    return render(request, 'login.html', {"form": form})


def logout(request):
    request.session.clear()
    return redirect("/login/")


def image_code(request):
    img, code_string = check_code()

    request.session["image_code"] = code_string
    request.session.set_expiry(60)

    stream = BytesIO()
    img.save(stream, 'png')
    return HttpResponse(stream.getvalue())
