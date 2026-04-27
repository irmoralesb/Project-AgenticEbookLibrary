namespace EbookLibraryUI.Services;

/// <summary>Simple page-navigation contract used by ViewModels.</summary>
public interface INavigationService
{
    void NavigateTo<TViewModel>() where TViewModel : notnull;
    void NavigateTo<TViewModel>(object parameter) where TViewModel : notnull;
    void GoBack();
}
