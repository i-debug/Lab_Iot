from django import forms
from django.shortcuts import render, redirect
from sensor.models import Admin
from sensor.utils.encrypt import md5


class BootStrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
                field.widget.attrs['placeholder'] = field.label
            else:
                field.widget.attrs = {'class': 'form-control', 'placeholder': field.label}


class AdminModelForm(BootStrapModelForm):

    confirm_password = forms.CharField(
        min_length=6,
        label='确认密码',
        widget=forms.PasswordInput(render_value=True)
    )

    class Meta:
        model = Admin
        fields = ["username", 'password', "confirm_password"]
        widgets = {
            'password': forms.PasswordInput(render_value=True)
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        return md5(password)

    def clean_confirm_password(self):
        print(self.cleaned_data)
        password = self.cleaned_data.get('password')
        confirm_password = md5(self.cleaned_data.get('confirm_password'))
        print(self.cleaned_data)

        if password != confirm_password:
            raise forms.ValidationError('两次密码不一致')
        return confirm_password


class AdminEditModelForm(BootStrapModelForm):

    class Meta:
        model = Admin
        fields = ["username",
                  # 'password'
                  ]
        # widgets = {
        #     'password': forms.PasswordInput(render_value=True)
        # }

class AdminResetModelForm(BootStrapModelForm):

    confirm_password = forms.CharField(
        min_length=6,
        label='确认密码',
        widget=forms.PasswordInput(render_value=True)
    )
    class Meta:
        model = Admin
        fields = ["password", "confirm_password"]
        widgets = {
            'password': forms.PasswordInput(render_value=True)
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        md5_pwd = md5(password)
        exists = Admin.objects.filter(id=self.instance.pk,password=md5_pwd).exists()
        if exists:
            raise forms.ValidationError('新密码不能与旧密码相同')
        return md5_pwd

    def clean_confirm_password(self):
        print(self.cleaned_data)
        password = self.cleaned_data.get('password')
        confirm_password = md5(self.cleaned_data.get('confirm_password'))
        print(self.cleaned_data)

        if password != confirm_password:
            raise forms.ValidationError('两次密码不一致')
        return confirm_password


def admin_add(request):
    title = "添加管理员"

    if request.method == "GET":
        form = AdminModelForm()
        return render(request, 'admin_change.html', {"form": form, "title": title})

    form = AdminModelForm(data=request.POST)

    if form.is_valid():
        form.save()
        # print("Form is valid")
        # print("Cleaned data:", form.cleaned_data)
        return redirect('/admin/list/')
    # else:
    #     print("Form is invalid")
    #     print("Error message:", form.errors)

    return render(request, 'admin_change.html', {"form": form, "title": title})


def admin_edit(request, nid):
    title = "编辑管理员"

    row_object = Admin.objects.filter(id=nid).first()
    if not row_object:
        return render(request, 'error.html', {"msg": "数据不存在"})

    if request.method == "GET":
        form = AdminEditModelForm(instance=row_object)
        return render(request, 'admin_change.html', {"form": form, "title": title})

    form = AdminEditModelForm(data=request.POST, instance=row_object)
    if form.is_valid():
        form.save()
        return redirect('/admin/list/')
    return render(request, 'admin_change.html', {"form": form, "title": title})


def admin_delete(request, nid):
    Admin.objects.filter(id=nid).delete()
    return redirect('/admin/list/')

def admin_reset(request,nid):
    row_object = Admin.objects.filter(id=nid).first()
    if not row_object:
        return redirect('/admin/list/')
    title = "重置密码-{}".format(row_object.username)
    if request.method == "GET":
        form = AdminResetModelForm()
        return render(request, 'admin_change.html', {"form": form, "title": title})

    form = AdminResetModelForm(data=request.POST,instance=row_object)
    if form.is_valid():
        form.save()
        return redirect('/admin/list/')
    return render(request, 'admin_change.html', {"form": form, "title": title})